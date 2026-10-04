"""Wiring the game-event features to the event bus.

The Hall of Deaths, pet cemetery, bedtime mode and the Oracle each react to log
events. This module creates them, hands each the small functions it needs
(running a game command, stopping the server, writing an audit entry) and
subscribes them to the bus, then starts the log follower. The features and the
availability flags they were imported under live on ``api.server`` and are read
through it at call time, so a value patched there is the one used here.
"""

from api import realtime, server


def _stop_server_for_bedtime():
    """Stop the server the way the rest of the project does."""
    _, stderr, code = server.run_script("manage.sh", "stop", timeout=600)
    if code != 0:
        raise RuntimeError(stderr or f"manage.sh stop returned {code}")


def _run_game_command(command):
    """Run a command for a feature that needs the server to see it."""
    _, stderr, code = server.run_rcon_command(command)
    if code != 0:
        raise RuntimeError(stderr or f"RCON returned {code}")


def _announce_in_game(command):
    """Run a command whose only purpose is to show players something.

    Raises on failure so the caller can record that the announcement did not
    reach anyone, which is the normal case when the server is stopped. The
    command runs exactly as any other game command does; this name is the
    Hall of Deaths' side of that, kept apart so it can say what it is for.
    """
    _run_game_command(command)


def start_event_capture():
    """Begin following the server log as soon as the API starts.

    Capture must not wait for a browser: events that happen while the dashboard
    is closed are exactly the ones worth recording. Tests skip this so no
    background thread or docker call escapes into the suite.
    """
    if not (server.SOCKETIO_AVAILABLE and server.socketio and server.EVENTS_AVAILABLE):
        return False

    bus = server.game_events.get_bus()
    bus.set_error_logger(server.app.logger.error)
    # Without this, the last few events on a quiet server stay buffered until
    # something else happens.
    bus.start_periodic_flush()

    if server.DEATHS_AVAILABLE:
        # The announcer is injected rather than imported by the hall, so the
        # hall stays testable without a server and without RCON.
        hall = server.hall_of_deaths.get_hall(announcer=_announce_in_game)
        hall.set_error_logger(server.app.logger.error)
        # Announcing makes a network call, and bus handlers run on the log
        # follower thread. The worker keeps an unreachable server from stalling
        # event processing behind each death.
        hall.start_worker()
        bus.subscribe(hall.handle_event)

    if server.PET_CEMETERY_AVAILABLE:
        # Same injection pattern as the hall above: the runner is passed in
        # rather than imported, so the cemetery stays testable without RCON.
        cemetery = server.pet_cemetery.get_cemetery(runner=_run_game_command)
        cemetery.set_error_logger(server.app.logger.error)
        cemetery.start_worker()
        bus.subscribe(cemetery.handle_event)

    if server.BEDTIME_AVAILABLE:
        bed = server.bedtime_mode.get_bedtime(runner=_run_game_command, stopper=_stop_server_for_bedtime)
        bed.set_error_logger(server.app.logger.error)
        # Stopping the server is not enough on its own: a restart policy or the
        # update timer can bring it back and reopen the evening. Turning joins
        # away during the closed window is what actually holds the line.
        bus.subscribe(bed.on_player_join)
        bed.start()

    if server.ORACLE_AVAILABLE:
        # Same injection pattern as pet_cemetery above. The audit logger is
        # its own callable, not a direct server.log_audit_event() call from inside
        # api/oracle.py: that function reads Flask's request proxy when
        # ip_address isn't passed explicitly, and the Oracle's worker thread
        # has no request context, so the sentinel below is passed here.
        orc = server.oracle.get_oracle(runner=_run_game_command)
        orc.set_error_logger(server.app.logger.error)
        orc.set_audit_logger(
            lambda player, action, details: server.log_audit_event(player, action, details, ip_address="minecraft-chat")
        )
        orc.start_worker()
        bus.subscribe(orc.handle_event)

    realtime.ensure_log_reader()
    return True
