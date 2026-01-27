import React, { useState, useEffect } from 'react';
import { Terminal, Activity, Database, CheckCircle, AlertCircle, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

// Try to import local data, fallback to empty if missing
let initialData = [];
try {
  // Note: specific path as per project structure
  import('../../new_golden_set.json').then(module => {
    initialData = module.default;
  }).catch(e => console.error("Could not load data", e));
} catch (e) {
  console.log("Data load failed or not in build");
}

const Card = ({ className, children }) => (
  <div className={cn("rounded-lg border border-border bg-card text-card-foreground shadow-sm", className)}>
    {children}
  </div>
);

const Badge = ({ variant = "default", className, children }) => {
  const variants = {
    default: "bg-primary/10 text-primary border-primary/20",
    secondary: "bg-secondary text-secondary-foreground",
    outline: "text-foreground border-border",
    destructive: "bg-destructive/10 text-red-400 border-red-900/50",
    warning: "bg-yellow-500/10 text-yellow-400 border-yellow-900/50",
  };
  return (
    <div className={cn("inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 font-mono", variants[variant], className)}>
      {children}
    </div>
  );
};

export default function App() {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  // Simulation of loading delay
  useEffect(() => {
    const timer = setTimeout(() => {
      // Re-fetch or re-set data if import promise resolved late
      import('../../new_golden_set.json').then(module => {
        setData(module.default);
        setLoading(false);
      }).catch(() => setLoading(false));
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  const stats = {
    total: data.length,
    picks: data.reduce((acc, item) => acc + (item.expected_picks?.length || 0), 0),
    sources: new Set(data.map(d => d.source)).size,
    pending: data.reduce((acc, item) => acc + (item.expected_picks?.filter(p => p.verified_grade === 'PENDING').length || 0), 0)
  };

  const filteredData = data.filter(item => 
    item.text.toLowerCase().includes(filter.toLowerCase()) || 
    item.source.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/20 p-8">
      {/* Header */}
      <header className="mb-12 border-b border-border pb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center border border-primary/20">
              <Terminal className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight font-mono">RALPH LOOP // <span className="text-primary">ITERATION 9</span></h1>
              <p className="text-muted-foreground text-sm font-mono">CORTEX VISUALIZER // V0.0.9</p>
            </div>
          </div>
          <div className="flex gap-4">
             <div className="text-right">
                <p className="text-xs text-muted-foreground font-mono">SYSTEM STATUS</p>
                <div className="flex items-center gap-2 text-green-500 font-mono text-sm">
                   <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                   OPTIMIZED
                </div>
             </div>
          </div>
        </div>

        {/* HUD Stats */}
        <div className="grid grid-cols-4 gap-4 mt-8">
          <Card className="p-4 flex flex-col justify-between hover:border-primary/50 transition-colors">
            <span className="text-xs text-muted-foreground font-mono mb-1">RAW MESSAGES</span>
            <span className="text-3xl font-bold font-mono">{stats.total}</span>
          </Card>
           <Card className="p-4 flex flex-col justify-between hover:border-primary/50 transition-colors">
            <span className="text-xs text-muted-foreground font-mono mb-1">EXTRACTED PICKS</span>
            <span className="text-3xl font-bold font-mono text-primary">{stats.picks}</span>
          </Card>
           <Card className="p-4 flex flex-col justify-between hover:border-primary/50 transition-colors">
            <span className="text-xs text-muted-foreground font-mono mb-1">ACTIVE SOURCES</span>
            <span className="text-3xl font-bold font-mono">{stats.sources}</span>
          </Card>
           <Card className="p-4 flex flex-col justify-between hover:border-primary/50 transition-colors">
            <span className="text-xs text-muted-foreground font-mono mb-1">PENDING VERIFICATION</span>
            <span className="text-3xl font-bold font-mono text-yellow-500">{stats.pending}</span>
          </Card>
        </div>
      </header>

      {/* Main Content */}
      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Feed */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
             <h2 className="text-lg font-semibold flex items-center gap-2">
                <Database className="h-4 w-4" />
                Data Stream
             </h2>
             <div className="relative w-64">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <input 
                  type="text" 
                  placeholder="Filter stream..." 
                  className="w-full bg-secondary/50 border border-border rounded-md py-2 pl-8 pr-4 text-sm focus:outline-none focus:border-primary/50 transition-colors font-mono"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                />
             </div>
          </div>

          <div className="space-y-4">
            <AnimatePresence>
              {loading ? (
                 <div className="text-center py-20 text-muted-foreground font-mono animate-pulse">
                    INITIALIZING CORTEX CONNECTION...
                 </div>
              ) : filteredData.length === 0 ? (
                 <div className="text-center py-20 text-muted-foreground font-mono">
                    NO DATA FOUND IN SECTOR
                 </div>
              ) : (
                filteredData.map((item, idx) => (
                  <motion.div 
                    key={item.id || idx}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <Card className="overflow-hidden group">
                      <div className="border-b border-border bg-secondary/20 p-3 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{item.source}</Badge>
                          <span className="text-xs text-muted-foreground font-mono">{item.date}</span>
                        </div>
                        <span className="text-xs font-mono text-muted-foreground">ID: {item.id}</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2">
                        {/* Raw Text */}
                        <div className="p-4 border-r border-border bg-background/50 relative">
                           <div className="absolute top-2 right-2 text-[10px] text-muted-foreground font-mono uppercase tracking-widest opacity-50">Raw</div>
                           <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed h-full max-h-[300px] overflow-y-auto custom-scrollbar">
                              {item.text}
                           </pre>
                        </div>
                        
                        {/* Extracted Picks */}
                        <div className="p-4 bg-secondary/5">
                           <div className="mb-2 flex justify-between items-center">
                              <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest opacity-50">Extraction</span>
                              <Badge variant="default" className="text-[10px]">{item.expected_picks?.length || 0} PICKS</Badge>
                           </div>
                           <div className="space-y-2">
                              {item.expected_picks?.map((pick, pIdx) => (
                                <div key={pIdx} className="bg-background border border-border rounded p-2 text-sm hover:border-primary/30 transition-colors">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="font-semibold text-primary">{pick.pick}</span>
                                    <span className="font-mono text-xs">{pick.odds > 0 ? `+${pick.odds}` : pick.odds}</span>
                                  </div>
                                  <div className="flex justify-between items-center text-xs text-muted-foreground">
                                    <span>{pick.league} • {pick.type}</span>
                                    <span className="font-mono">{pick.units}u</span>
                                  </div>
                                </div>
                              ))}
                           </div>
                        </div>
                      </div>
                    </Card>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Right Column: Analytics */}
        <div className="space-y-6">
          <Card className="p-6 sticky top-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
               <Activity className="h-4 w-4" />
               Performance Metrics
            </h3>
            
            <div className="space-y-6">
               <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                     <span className="text-muted-foreground">Recall Rate</span>
                     <span className="font-mono font-bold">92.5%</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                     <div className="h-full bg-primary w-[92.5%]" />
                  </div>
               </div>

               <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                     <span className="text-muted-foreground">Precision</span>
                     <span className="font-mono font-bold text-yellow-500">88.2%</span>
                  </div>
                  <div className="h-2 bg-secondary rounded-full overflow-hidden">
                     <div className="h-full bg-yellow-500 w-[88.2%]" />
                  </div>
               </div>

               <div className="mt-8 pt-6 border-t border-border">
                  <h4 className="text-xs font-mono text-muted-foreground uppercase tracking-widest mb-4">Active Models</h4>
                  <div className="space-y-3">
                     <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                           <div className="h-1.5 w-1.5 rounded-full bg-green-500" />
                           Llama 3.1 8b
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">PRIMARY</span>
                     </div>
                     <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                           <div className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
                           Mistral 7B
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">FALLBACK</span>
                     </div>
                     <div className="flex items-center justify-between text-sm opacity-50">
                        <span className="flex items-center gap-2">
                           <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
                           Groq 70B
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">RATE LIMITED</span>
                     </div>
                  </div>
               </div>
            </div>
          </Card>
        </div>

      </main>
    </div>
  );
}
