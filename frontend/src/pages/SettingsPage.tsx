import React from 'react';
import * as Icons from 'lucide-react';
import { useToast } from '../shared/components/Toast';

export const SettingsPage: React.FC = () => {
  const [orgId, setOrgId] = React.useState('');
  const [orgName, setOrgName] = React.useState('');
  const [orgSlug, setOrgSlug] = React.useState('');
  const [envMode, setEnvMode] = React.useState('Development');
  
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const { showToast } = useToast();

  const [error, setError] = React.useState<string | null>(null);

  const fetchSettings = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Get the list of organizations to resolve the active context dynamically
      const listRes = await fetch('/api/v1/organizations');
      if (!listRes.ok) throw new Error('Failed to fetch organization context from server');
      const orgs = await listRes.json();
      
      const activeOrg = orgs[0] || { slug: 'my-personal-org' };
      
      // 2. Fetch detailed settings for the active organization slug/id
      const detailRes = await fetch(`/api/v1/organizations/${activeOrg.slug}`);
      if (!detailRes.ok) throw new Error('Failed to retrieve organization settings');
      const data = await detailRes.json();
      
      setOrgId(data.id);
      setOrgName(data.name || 'My Personal Org');
      setOrgSlug(data.slug || 'my-personal-org');
      setEnvMode(data.settings?.environment_mode || 'Development');
    } catch (err: any) {
      setError(err.message || 'Unable to connect to settings service.');
      showToast(err.message || 'Error loading settings', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  React.useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName.trim() || !orgSlug.trim()) {
      showToast('Organization name and slug cannot be empty.', 'warning');
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`/api/v1/organizations/${orgId || orgSlug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: orgName.trim(),
          slug: orgSlug.trim(),
          environment_mode: envMode,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save settings');
      }

      showToast('Workspace settings saved successfully.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 h-full p-6 text-left bg-background overflow-y-auto">
      <div className="flex items-center gap-2 mb-6">
        <Icons.Sliders className="text-primary" size={20} />
        <h2 className="font-bold text-lg text-foreground">Workspace Settings</h2>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <Icons.Loader2 className="animate-spin text-primary" size={24} />
          <span className="text-xs font-medium">Loading workspace settings...</span>
        </div>
      ) : error ? (
        <div className="border border-destructive/30 bg-destructive/5 rounded-2xl p-8 text-center flex flex-col items-center gap-3 max-w-md">
          <Icons.AlertCircle className="text-destructive" size={32} />
          <div>
            <h3 className="font-bold text-sm text-foreground mb-1">Failed to load settings</h3>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>
          <button
            onClick={fetchSettings}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white text-xs font-bold rounded-xl transition-all cursor-pointer shadow-md"
          >
            <Icons.RotateCw size={13} />
            Retry Request
          </button>
        </div>
      ) : (
        <form onSubmit={handleSave} className="max-w-md border border-border rounded-2xl bg-card p-5 shadow-lg space-y-4">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Organization Name</label>
            <input
              type="text"
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              disabled={saving}
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Organization Slug</label>
            <input
              type="text"
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              value={orgSlug}
              onChange={(e) => setOrgSlug(e.target.value)}
              disabled={saving}
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1">Environment Mode</label>
            <select
              className="w-full bg-background border border-border rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              value={envMode}
              onChange={(e) => setEnvMode(e.target.value)}
              disabled={saving}
            >
              <option value="Development">Development</option>
              <option value="Staging">Staging</option>
              <option value="Production">Production</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-xl shadow-lg shadow-primary/20 transition-all disabled:opacity-50 cursor-pointer"
          >
            {saving && <Icons.Loader className="animate-spin" size={13} />}
            <span>Save Settings</span>
          </button>
        </form>
      )}
    </div>
  );
};
export default SettingsPage;
