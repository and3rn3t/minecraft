import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { PageHeader } from '../components/ui/PageHeader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '../components/ui/Table';
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

  const getRoleBadgeStatus = role => {
    switch (role) {
      case 'admin':
        return 'danger';
      case 'operator':
        return 'info';
      default:
        return 'neutral';
    }
  };

  return (
    <div>
      <PageHeader title="USER MANAGEMENT" />

      {/* Error/Success messages */}
      {error && <ErrorState message={error} />}

      {success && (
        <Alert tone="success" autoDismiss={5000} onDismiss={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Role Selection Modal */}
      <Modal
        open={!!showRoleModal}
        onClose={() => setShowRoleModal(null)}
        title={showRoleModal ? `CHANGE ROLE FOR ${showRoleModal.username.toUpperCase()}` : ''}
      >
        {showRoleModal && (
          <>
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
                      ? 'bg-minecraft-grass cursor-not-allowed'
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
            <Button className="w-full" onClick={() => setShowRoleModal(null)}>
              CANCEL
            </Button>
          </>
        )}
      </Modal>

      {/* Users Table */}
      <Card padding="lg">
        {loading ? (
          <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
            LOADING USERS...
          </div>
        ) : users.length === 0 ? (
          <EmptyState icon="👤" title="No users found" />
        ) : (
          <Table caption="Registered users">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Username</TableHeaderCell>
                <TableHeaderCell>Role</TableHeaderCell>
                <TableHeaderCell>Email</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Created</TableHeaderCell>
                <TableHeaderCell>Actions</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user, index) => (
                <TableRow key={user.username || `user-${index}`} className="hover:bg-minecraft-dirt">
                  <TableCell>
                    {user.username}
                    {user.username === currentUser?.username && (
                      <span className="ml-2 text-[8px] text-minecraft-text-dark">(YOU)</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge status={getRoleBadgeStatus(user.role)}>
                      {(user.role || 'user').toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-minecraft-text-dark">
                    {user.email || <span className="italic">NO EMAIL</span>}
                  </TableCell>
                  <TableCell>
                    <Badge status={user.enabled ? 'success' : 'danger'}>
                      {user.enabled ? '✓ ENABLED' : '✗ DISABLED'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-minecraft-text-dark">
                    {formatDate(user.created)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
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
                      >
                        CHANGE ROLE
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleToggle(user.username, user.enabled)}
                        disabled={
                          updating === user.username ||
                          deleting === user.username ||
                          user.username === currentUser?.username
                        }
                      >
                        {updating === user.username ? '...' : user.enabled ? 'DISABLE' : 'ENABLE'}
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(user.username)}
                        disabled={
                          updating === user.username ||
                          deleting === user.username ||
                          user.username === currentUser?.username
                        }
                      >
                        {deleting === user.username ? 'DELETING...' : 'DELETE'}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Info */}
      {users.length > 0 && (
        <div className="mt-4 bg-minecraft-water/30 border-2 border-minecraft-water-dark p-3 text-[10px] font-minecraft text-minecraft-text-light">
          <strong>INFO:</strong> {users.length} USER{users.length !== 1 ? 'S' : ''} REGISTERED. YOU
          CANNOT MODIFY OR DELETE YOUR OWN ACCOUNT. AT LEAST ONE ADMIN USER MUST ALWAYS EXIST.
        </div>
      )}
    </div>
  );
};

export default Users;
