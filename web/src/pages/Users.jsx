import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

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
        return 'bg-red-900/50 text-red-300';
      case 'operator':
        return 'bg-blue-900/50 text-blue-300';
      case 'user':
        return 'bg-gray-700 text-gray-300';
      default:
        return 'bg-gray-700 text-gray-300';
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">User Management</h1>
      </div>

      {/* Error/Success messages */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded p-4 mb-6 text-red-300">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-900/50 border border-green-700 rounded p-4 mb-6 text-green-300">
          {success}
        </div>
      )}

      {/* Role Selection Modal */}
      {showRoleModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700">
            <h2 className="text-2xl font-semibold mb-4">
              Change Role for {showRoleModal.username}
            </h2>
            <p className="text-gray-400 mb-4">Current role: {showRoleModal.currentRole}</p>
            <div className="space-y-2 mb-6">
              {Object.keys(roles).map(role => (
                <button
                  key={role}
                  onClick={() => handleUpdateRole(showRoleModal.username, role)}
                  disabled={updating === showRoleModal.username || role === showRoleModal.currentRole}
                  className={`w-full px-4 py-2 rounded transition-colors text-left ${
                    role === showRoleModal.currentRole
                      ? 'bg-primary-600 text-white cursor-not-allowed'
                      : 'bg-gray-700 hover:bg-gray-600 text-white'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium capitalize">{role}</span>
                    <span className="text-sm text-gray-400">
                      {roles[role]?.permission_count || 0} permissions
                    </span>
                  </div>
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowRoleModal(null)}
              className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-gray-800 rounded-lg p-6">
        {loading ? (
          <div className="text-center py-8">Loading users...</div>
        ) : users.length === 0 ? (
          <div className="text-gray-400 text-center py-8">
            <p className="text-lg mb-2">No users found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4">Username</th>
                  <th className="text-left py-3 px-4">Role</th>
                  <th className="text-left py-3 px-4">Email</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Created</th>
                  <th className="text-left py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user, index) => (
                  <tr
                    key={user.username || `user-${index}`}
                    className="border-b border-gray-700 hover:bg-gray-700 transition-colors"
                  >
                    <td className="py-3 px-4 font-medium">
                      {user.username}
                      {user.username === currentUser?.username && (
                        <span className="ml-2 text-xs text-gray-400">(You)</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${getRoleColor(
                          user.role
                        )}`}
                      >
                        {user.role || 'user'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {user.email || <span className="italic">No email</span>}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          user.enabled
                            ? 'bg-green-900/50 text-green-300'
                            : 'bg-red-900/50 text-red-300'
                        }`}
                      >
                        {user.enabled ? '✓ Enabled' : '✗ Disabled'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">{formatDate(user.created)}</td>
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
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
                        >
                          Change Role
                        </button>
                        <button
                          onClick={() => handleToggle(user.username, user.enabled)}
                          disabled={
                            updating === user.username ||
                            deleting === user.username ||
                            user.username === currentUser?.username
                          }
                          className={`px-3 py-1 rounded text-sm transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed ${
                            user.enabled
                              ? 'bg-yellow-600 hover:bg-yellow-700'
                              : 'bg-green-600 hover:bg-green-700'
                          }`}
                        >
                          {updating === user.username
                            ? '...'
                            : user.enabled
                              ? 'Disable'
                              : 'Enable'}
                        </button>
                        <button
                          onClick={() => handleDelete(user.username)}
                          disabled={
                            updating === user.username ||
                            deleting === user.username ||
                            user.username === currentUser?.username
                          }
                          className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm transition-colors"
                        >
                          {deleting === user.username ? 'Deleting...' : 'Delete'}
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
        <div className="mt-4 bg-blue-900/30 border border-blue-700 rounded p-3 text-blue-300 text-sm">
          <strong>Info:</strong> {users.length} user{users.length !== 1 ? 's' : ''} registered.
          You cannot modify or delete your own account. At least one admin user must always exist.
        </div>
      )}
    </div>
  );
};

export default Users;

