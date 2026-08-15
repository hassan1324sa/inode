import React from 'react';
import * as Icons from 'lucide-react';
import { useToast } from '../shared/components/Toast';
import { authenticatedFetch } from '../shared/api/authenticatedFetch';

interface CredentialItem {
  credential_id: string;
}

export const CredentialsPage: React.FC = () => {
  const [credentials, setCredentials] = React.useState<CredentialItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const { showToast } = useToast();

  // Modals state
  const [isAddOpen, setIsAddOpen] = React.useState(false);
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [selectedCredId, setSelectedCredId] = React.useState('');

  // Form states (kept strictly inside local component state and cleared after submit)
  const [newCredName, setNewCredName] = React.useState('');
  const [newCredProvider, setNewCredProvider] = React.useState('google');
  const [newCredValue, setNewCredValue] = React.useState('');
  const [rotateValue, setRotateValue] = React.useState('');

  const [error, setError] = React.useState<string | null>(null);

  const fetchCredentials = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authenticatedFetch('/api/v1/debug/credentials');
      if (!res.ok) throw new Error('Failed to load credentials from backend');
      const data = await res.json();
      setCredentials(data.credentials || []);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to credentials service.');
      showToast(err.message || 'Error loading credentials', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  React.useEffect(() => {
    fetchCredentials();
  }, [fetchCredentials]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCredName.trim() || !newCredValue.trim()) {
      showToast('Please enter both name and secret key value.', 'warning');
      return;
    }

    try {
      const res = await authenticatedFetch('/api/v1/debug/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newCredName.trim(),
          provider: newCredProvider,
          value: newCredValue.trim(),
        }),
      });

      if (!res.ok) throw new Error('Failed to create credential');
      showToast(`Credential "${newCredName}" created successfully.`, 'success');
      
      // Clean local secret memory immediately
      setNewCredName('');
      setNewCredValue('');
      setIsAddOpen(false);
      
      fetchCredentials();
    } catch (err: any) {
      showToast(err.message || 'Failed to create credential', 'error');
    }
  };

  const handleRotate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rotateValue.trim()) {
      showToast('Please enter a new secret key value to rotate.', 'warning');
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/v1/debug/credentials/${selectedCredId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: selectedCredId,
          provider: 'google', // backend requires provider parameter
          value: rotateValue.trim(),
        }),
      });

      if (!res.ok) throw new Error('Failed to rotate credential secret');
      showToast(`Credential "${selectedCredId}" secret rotated successfully.`, 'success');

      // Clean local secret memory immediately
      setRotateValue('');
      setIsEditOpen(false);
      
      fetchCredentials();
    } catch (err: any) {
      showToast(err.message || 'Failed to rotate credential secret', 'error');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Are you sure you want to delete the credential "${id}"?`)) return;

    try {
      const res = await authenticatedFetch(`/api/v1/debug/credentials/${id}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete credential');
      showToast(`Credential "${id}" deleted successfully.`, 'success');
      fetchCredentials();
    } catch (err: any) {
      showToast(err.message || 'Failed to delete credential', 'error');
    }
  };

  // Helper to determine provider color tags
  const getProviderColor = (name: string) => {
    const id = name.toLowerCase();
    if (id.includes('gemini') || id.includes('google')) return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
    if (id.includes('slack') || id.includes('bot')) return 'text-blue-400 border-blue-500/20 bg-blue-500/5';
    if (id.includes('openai') || id.includes('gpt')) return 'text-purple-400 border-purple-500/20 bg-purple-500/5';
    return 'text-amber-400 border-amber-500/20 bg-amber-500/5';
  };

  return (
    <div className="flex-1 h-full p-6 text-left bg-background overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Icons.Key className="text-primary" size={20} />
          <h2 className="font-bold text-lg text-foreground">API Credentials</h2>
        </div>
        <button
          onClick={() => setIsAddOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl shadow-lg shadow-primary/20 transition-all cursor-pointer"
        >
          <Icons.Plus size={14} />
          Add Credential
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <Icons.Loader2 className="animate-spin text-primary" size={24} />
          <span className="text-xs font-medium">Loading credentials...</span>
        </div>
      ) : error ? (
        <div className="border border-destructive/30 bg-destructive/5 rounded-2xl p-8 text-center flex flex-col items-center gap-3 max-w-md">
          <Icons.AlertCircle className="text-destructive" size={32} />
          <div>
            <h3 className="font-bold text-sm text-foreground mb-1">Failed to load credentials</h3>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>
          <button
            onClick={fetchCredentials}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white text-xs font-bold rounded-xl transition-all cursor-pointer shadow-md"
          >
            <Icons.RotateCw size={13} />
            Retry Request
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
          {credentials.map((cred) => (
            <div
              key={cred.credential_id}
              className="border border-border rounded-2xl bg-card p-4 shadow-md flex justify-between items-start transition-all hover:border-primary/30"
            >
              <div className="min-w-0 flex-1">
                <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${getProviderColor(cred.credential_id)}`}>
                  {cred.credential_id.split('-')[0] || 'API KEY'}
                </span>
                <h4 className="font-bold text-sm text-foreground mt-2 truncate pr-2">{cred.credential_id}</h4>
                <span className="text-[9px] text-muted-foreground font-mono">Reference Registered</span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => {
                    setSelectedCredId(cred.credential_id);
                    setIsEditOpen(true);
                  }}
                  className="p-2 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  title="Rotate Secret"
                >
                  <Icons.RefreshCw size={13} />
                </button>
                <button
                  onClick={() => handleDelete(cred.credential_id)}
                  className="p-2 rounded-lg hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors cursor-pointer"
                  title="Delete Key"
                >
                  <Icons.Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}

          {credentials.length === 0 && (
            <div className="col-span-full border border-dashed border-border rounded-2xl p-8 text-center flex flex-col items-center gap-2">
              <Icons.Key className="text-muted-foreground/40" size={32} />
              <div className="font-bold text-sm text-foreground">No credentials configured</div>
              <p className="text-xs text-muted-foreground max-w-xs">
                No API keys found. Click "Add Credential" above to connect your AI models and services.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Add Credential Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setIsAddOpen(false)}>
          <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl overflow-hidden text-left" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                <Icons.PlusSquare size={16} className="text-primary" />
                Add API Credential
              </h3>
              <button onClick={() => setIsAddOpen(false)} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground">
                <Icons.X size={15} />
              </button>
            </div>
            <form onSubmit={handleAdd} className="p-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Credential Name</label>
                <input
                  type="text"
                  placeholder="e.g. production-gemini-key"
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                  value={newCredName}
                  onChange={(e) => setNewCredName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Provider</label>
                <select
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                  value={newCredProvider}
                  onChange={(e) => setNewCredProvider(e.target.value)}
                >
                  <option value="google">Google Gemini</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="openrouter">OpenRouter</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">API Key / Secret Token</label>
                <input
                  type="password"
                  placeholder="Enter secret token value"
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                  value={newCredValue}
                  onChange={(e) => setNewCredValue(e.target.value)}
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 border border-border rounded-xl text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
                >
                  Save Credential
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rotate Secret Modal */}
      {isEditOpen && (
        <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setIsEditOpen(false)}>
          <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl overflow-hidden text-left" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                <Icons.RefreshCw size={14} className="text-primary animate-spin" />
                Rotate Secret: {selectedCredId}
              </h3>
              <button onClick={() => setIsEditOpen(false)} className="p-1 rounded hover:bg-secondary text-muted-foreground hover:text-foreground">
                <Icons.X size={15} />
              </button>
            </div>
            <form onSubmit={handleRotate} className="p-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Credential Name</label>
                <input
                  type="text"
                  className="w-full bg-secondary border border-border rounded-xl px-3 py-2 text-xs text-muted-foreground cursor-not-allowed"
                  value={selectedCredId}
                  disabled
                  readOnly
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">New API Key / Secret Token</label>
                <input
                  type="password"
                  placeholder="Enter new secret token value"
                  className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                  value={rotateValue}
                  onChange={(e) => setRotateValue(e.target.value)}
                  required
                />
                <p className="text-[10px] text-muted-foreground mt-1">The old secret is vaulted and cannot be read. Enter a new value to rotate it.</p>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="px-4 py-2 border border-border rounded-xl text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl shadow-md transition-all cursor-pointer"
                >
                  Rotate Secret
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default CredentialsPage;
