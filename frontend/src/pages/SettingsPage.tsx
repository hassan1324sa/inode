import React from 'react';
import * as Icons from 'lucide-react';

export const SettingsPage: React.FC = () => {
  return (
    <div className="flex-1 h-full p-6 text-left bg-background overflow-y-auto">
      <div className="flex items-center gap-2 mb-6">
        <Icons.Sliders className="text-primary" size={20} />
        <h2 className="font-bold text-lg text-foreground">Workspace Settings</h2>
      </div>

      <div className="max-w-md border border-border rounded-lg bg-slate-950/20 p-5 glass space-y-4">
        <div>
          <label className="text-xs font-semibold text-foreground block mb-1">Organization Slug</label>
          <input
            type="text"
            className="w-full bg-background/50 border border-border rounded-md px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
            value="my-personal-org"
            readOnly
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-foreground block mb-1">Environment Mode</label>
          <select className="w-full bg-background/50 border border-border rounded-md px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary">
            <option>Development</option>
            <option>Staging</option>
            <option>Production</option>
          </select>
        </div>

        <button className="px-4 py-1.5 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-md shadow-md shadow-primary/20 transition-all">
          Save Settings
        </button>
      </div>
    </div>
  );
};
export default SettingsPage;
