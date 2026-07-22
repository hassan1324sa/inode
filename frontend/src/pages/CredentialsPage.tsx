import React from 'react';
import * as Icons from 'lucide-react';

export const CredentialsPage: React.FC = () => {
  return (
    <div className="flex-1 h-full p-6 text-left bg-background overflow-y-auto">
      <div className="flex items-center gap-2 mb-6">
        <Icons.Key className="text-primary" size={20} />
        <h2 className="font-bold text-lg text-foreground">API Credentials</h2>
      </div>

      <div className="grid grid-cols-2 gap-4 max-w-2xl">
        <div className="border border-border rounded-lg bg-slate-950/20 p-4 glass flex justify-between items-start">
          <div>
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wide">Gemini API</span>
            <h4 className="font-semibold text-xs text-foreground mt-1">my-gemini-key</h4>
            <span className="text-[9px] text-muted-foreground font-mono">Last modified: 1 day ago</span>
          </div>
          <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground">
            <Icons.Edit3 size={12} />
          </button>
        </div>

        <div className="border border-border rounded-lg bg-slate-950/20 p-4 glass flex justify-between items-start">
          <div>
            <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wide">Slack Bot Token</span>
            <h4 className="font-semibold text-xs text-foreground mt-1">slack-auth-key</h4>
            <span className="text-[9px] text-muted-foreground font-mono">Last modified: 3 days ago</span>
          </div>
          <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground">
            <Icons.Edit3 size={12} />
          </button>
        </div>
      </div>

      <button className="mt-6 flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/95 text-white text-xs font-bold rounded-md shadow-md shadow-primary/20 transition-all">
        <Icons.Plus size={14} />
        Add Credential
      </button>
    </div>
  );
};
export default CredentialsPage;
