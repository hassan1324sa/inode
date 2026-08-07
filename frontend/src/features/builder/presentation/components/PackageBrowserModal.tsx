import React, { useState } from 'react';
import * as Icons from 'lucide-react';
import { useToast } from '../../../../shared/components/Toast';

interface PackageItem {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  installed: boolean;
  category: string;
}

interface PackageBrowserModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PackageBrowserModal: React.FC<PackageBrowserModalProps> = ({ isOpen, onClose }) => {
  const [packages, setPackages] = useState<PackageItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'installed'>('all');
  const { showToast } = useToast();

  const fetchPackages = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/packages/');
      if (!res.ok) throw new Error('Failed to load packages');
      const data = await res.json();
      setPackages(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to load packages', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  React.useEffect(() => {
    if (isOpen) {
      fetchPackages();
    }
  }, [isOpen, fetchPackages]);

  if (!isOpen) return null;

  const handleToggleInstall = async (name: string, currentlyInstalled: boolean) => {
    const endpoint = currentlyInstalled ? '/api/v1/packages/uninstall' : '/api/v1/packages/install';
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_name: name })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Operation failed');
      }
      showToast(
        currentlyInstalled ? `Removed package ${name}` : `Installed package ${name}`,
        currentlyInstalled ? 'info' : 'success'
      );
      fetchPackages();
    } catch (err: any) {
      showToast(err.message || 'Operation failed', 'error');
    }
  };

  const filtered = packages.filter((pkg) => {
    if (activeTab === 'installed' && !pkg.installed) return false;
    if (search && !pkg.name.toLowerCase().includes(search.toLowerCase()) && !pkg.description.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[80vh] text-left"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Icons.Package className="text-primary" size={20} />
            <h2 className="font-bold text-sm text-foreground">Package & Plugin Browser</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/10 rounded-lg transition-colors text-muted-foreground hover:text-foreground"
          >
            <Icons.X size={16} />
          </button>
        </div>

        {/* Tabs & Search */}
        <div className="flex items-center justify-between gap-4 p-4 border-b border-border bg-secondary/30">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'all' ? 'bg-primary text-white shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Marketplace
            </button>
            <button
              onClick={() => setActiveTab('installed')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'installed'
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Installed ({packages.filter((p) => p.installed).length})
            </button>
          </div>

          <div className="relative w-64">
            <Icons.Search className="absolute left-3 top-2.5 text-muted-foreground" size={14} />
            <input
              type="text"
              placeholder="Search packages..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs bg-secondary text-foreground focus:outline-none focus:ring-1 focus:ring-primary skeuo-sunken"
            />
          </div>
        </div>

        {/* Package List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 relative min-h-[200px]">
          {loading && (
            <div className="absolute inset-0 bg-card/65 backdrop-blur-sm z-10 flex items-center justify-center text-xs text-muted-foreground">
              <Icons.Loader className="animate-spin text-primary mr-2" size={16} />
              Synchronizing packages...
            </div>
          )}
          {filtered.map((pkg) => (
            <div
              key={pkg.id}
              className="flex items-center justify-between p-4 rounded-xl border border-border/60 bg-secondary/20 hover:border-border transition-all"
            >
              <div className="flex flex-col gap-1 pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-foreground">{pkg.name}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-muted-foreground font-mono">
                    v{pkg.version}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-primary/20 text-primary">
                    {pkg.category}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{pkg.description}</p>
                <span className="text-[11px] text-muted-foreground/80 mt-1">By {pkg.author}</span>
              </div>

              <button
                onClick={() => handleToggleInstall(pkg.name, pkg.installed)}
                disabled={loading}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 border ${
                  pkg.installed
                    ? 'bg-secondary text-foreground border-border hover:bg-destructive hover:text-white hover:border-destructive'
                    : 'bg-primary text-white border-primary hover:bg-primary/90 shadow-sm'
                }`}
              >
                {pkg.installed ? 'Installed' : 'Install'}
              </button>
            </div>
          ))}

          {filtered.length === 0 && !loading && (
            <div className="text-center py-12 text-muted-foreground text-xs">
              No packages found matching your criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default PackageBrowserModal;
