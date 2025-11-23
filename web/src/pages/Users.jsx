import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

const Users = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showRoleModal, setShowRoleModal] = useState(null);
  const { user: currentUser } = useAuth();

  useEffect(() => {
    loadData();
  }, []);

  // Clear messages after 5 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [usersData, rolesData] = await Promise.all([
        api.listUsers(),
        api.listRoles(),
      ]);
      setUsers(usersData.users || []);
      setRoles(rolesData.roles || {});
    } catch (err) {
      setError('Failed to load users');
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateRole = async (username, newRole) => {
    setUpdating(username);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.updateUserRole(username, newRole);
      setSuccess(result.message || 'User role updated successfully');
      setShowRoleModal(null);
      loadData();
    } catch (err) {
      setError(
        err.response?.data?.error || err.message || 'Failed to update user role'
      );
      console.error('Failed to update user role:', err);
    } finally {
      setUpdating(null);
    }
  };

  const handleDelete = async username => {
    if (
      !window.confirm(
        `Are you sure you want to delete user "${username}"?\n\nThis action cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(username);
    setError(null);
    setSuccess(null);

    try {
      const result = await api.deleteUser(username);
      setSuccess(result.message || 'User deleted successfully');
      loadData();
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to delete user');
      console.error('Failed to delete user:', err);
    } finally {
      setDeleting(null);
    }
  };

  const handleToggle = async (username, enabled) => {
    setUpdating(username);
    setError(null);
    setSuccess(null);

    try {
      const result = enabled
        ? await api.disableUser(username)
        : await api.enableUser(username);
      setSuccess(result.message || `User ${enabled ? 'disabled' : 'enabled'} successfully`);
      loadData();
    } catch (err) {
      setError(
        err.response?.data?.error ||
          err.message ||
          `Failed to ${enabled ? 'disable' : 'enable'} user`
      );
      console.error('Failed to toggle user:', err);
    } finally {
      setUpdating(null);
    }
  };

  const formatDate = dateString => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const getRoleColor = role => {
    switch (role) {
      case 'admin':
        return 'bg-[#C62828] text-white';
      case 'operator':
        return 'bg-minecraft-water-DEFAULT text-white';
      case 'user':
        return 'bg-minecraft-stone-DEFAULT text-white';
      default:
        return 'bg-minecraft-stone-DEFAULT text-white';
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-minecraft text-minecraft-grass-light leading-tight">
          USER MANAGEMENT
        </h1>
      </div>

      {/* Error/Success messages */}
      {error && (
        <div className="bg-[#C62828] border-2 border-[#B71C1C] p-4 mb-6 text-white text-[10px] font-minecraft">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-minecraft-grass-DEFAULT border-2 border-minecraft-grass-dark p-4 mb-6 text-white text-[10px] font-minecraft">
          {success}
        </div>
      )}

      {/* Role Selection Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="card-minecraft p-6 w-full max-w-md">
            <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 leading-tight">
              CHANGE ROLE FOR {showRoleModal.username.toUpperCase()}
            </h2>
            <p className="text-[10px] font-minecraft text-minecraft-text-dark mb-4">
              CURRENT ROLE: {showRoleModal.currentRole.toUpperCase()}
            </p>
            <div className="space-y-2 mb-6">
              {Object.keys(roles).map(role => (
                <button
                  key={role}
                  onClick={() => handleUpdateRole(showRoleModal.username, role)}
                  disabled={updating === showRoleModal.username || role === showRoleModal.currentRole}
                  className={`w-full btn-minecraft text-[10px] text-left ${
                    role === showRoleModal.currentRole
                      ? 'bg-minecraft-grass-DEFAULT cursor-not-allowed'
                      : ''
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-minecraft uppercase">{role}</span>
                    <span className="text-[8px] font-minecraft text-minecraft-text-dark">
                      {roles[role]?.permission_count || 0} PERMISSIONS
                    </span>
                  </div>
                </button>
              ))}
            </div>
            <button onClick={() => setShowRoleModal(null)} className="btn-minecraft w-full text-[10px]">
              CANCEL
            </button>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="card-minecraft p-6">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING USERS...
          </div>
        ) : users.length === 0 ? (
          <div className="text-minecraft-text-dark text-center py-8">
            <p className="text-sm font-minecraft mb-2">NO USERS FOUND</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-[#5D4037]">
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    USERNAME
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    ROLE
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    EMAIL
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    STATUS
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    CREATED
                  </th>
                  <th className="text-left py-3 px-4 text-[10px] font-minecraft text-minecraft-text-light uppercase">
                    ACTIONS
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user, index) => (
                  <tr
                    key={user.username || `user-${index}`}
                    className="border-b-2 border-[#5D4037] hover:bg-minecraft-dirt-DEFAULT"
                  >
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-light">
                      {user.username}
                      {user.username === currentUser?.username && (
                        <span className="ml-2 text-[8px] text-minecraft-text-dark">(YOU)</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 text-[8px] font-minecraft ${getRoleColor(user.role)}`}
                      >
                        {(user.role || 'user').toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-dark">
                      {user.email || <span className="italic">NO EMAIL</span>}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 text-[8px] font-minecraft ${
                          user.enabled
                            ? 'bg-minecraft-grass-DEFAULT text-white'
                            : 'bg-[#C62828] text-white'
                        }`}
                      >
                        {user.enabled ? '✓ ENABLED' : '✗ DISABLED'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-minecraft text-[10px] text-minecraft-text-dark">
                      {formatDate(user.created)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() =>
                            setShowRoleModal({
                              username: user.username,
                              currentRole: user.role,
                            })
                          }
                          disabled={
                            updating === user.username ||
                            deleting === user.username ||
                            user.username === currentUser?.username
                          }
                          className="btn-minecraft text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          CHANGE ROLE
                        </button>
                        <button
                          onClick={() => handleToggle(user.username, user.enabled)}
                          disabled={
                            updating === user.username ||
                            deleting === user.username ||
                            user.username === currentUser?.username
                          }
                          className={`btn-minecraft text-[8px] disabled:opacity-50 disabled:cursor-not-allowed ${
                            user.enabled ? '' : 'bg-minecraft-grass-DEFAULT'
                          }`}
                        >
                          {updating === user.username
                            ? '...'
                            : user.enabled
                              ? 'DISABLE'
                              : 'ENABLE'}
                        </button>
                        <button
                          onClick={() => handleDelete(user.username)}
                          disabled={
                            updating === user.username ||
                            deleting === user.username ||
                            user.username === currentUser?.username
                          }
                          className="btn-minecraft-danger text-[8px] disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {deleting === user.username ? 'DELETING...' : 'DELETE'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info */}
      {users.length > 0 && (
        <div className="mt-4 bg-minecraft-water-DEFAULT/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
          <strong>INFO:</strong> {users.length} USER{users.length !== 1 ? 'S' : ''} REGISTERED. YOU
          CANNOT MODIFY OR DELETE YOUR OWN ACCOUNT. AT LEAST ONE ADMIN USER MUST ALWAYS EXIST.
        </div>
      )}
    </div>
  );
};

export default Users;

