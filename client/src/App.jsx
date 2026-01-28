import React, { useState, useEffect } from 'react';
import { Terminal, Activity, Database, Search, ChevronDown, ChevronUp, Zap, Radio } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

// Mock Data Load (Replaced by Live Fetch in Iteration 11)
let initialData = [];

const Card = ({ className, children, hoverEffect = true }) => (
  <motion.div 
    layout
    className={cn(
      "rounded-none bg-card/50 text-card-foreground backdrop-blur-sm", 
      hoverEffect && "hover:bg-secondary/20 transition-colors duration-300",
      className
    )}
  >
    {children}
  </motion.div>
);

const Badge = ({ variant = "default", className, children }) => {
  const variants = {
    default: "bg-primary/20 text-primary border-primary/20",
    secondary: "bg-secondary text-secondary-foreground",
    outline: "text-muted-foreground border-border bg-transparent",
    destructive: "bg-destructive/20 text-red-400 border-red-900/50",
    warning: "bg-yellow-500/10 text-yellow-400 border-yellow-900/50",
  };
  return (
    <div className={cn("inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] uppercase tracking-wider font-mono transition-colors", variants[variant], className)}>
      {children}
    </div>
  );
};

export default function App() {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  // Ralph Loop Iteration 32: High Velocity Stress Test
  const fetchData = async () => {
    try {
      const response = await fetch('/latest_picks.json');
      if (!response.ok) throw new Error("Data stream offline");
      const jsonData = await response.json();
      setData(jsonData);
      setLoading(false);
    } catch (error) {
      console.warn("Live feed disconnected, retrying...", error);
      // Keep loading true if we have NO data, otherwise keep showing old data
      if (data.length === 0) setLoading(false); 
    }
  };

  useEffect(() => {
    // Initial Fetch
    fetchData();

    // Poll every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
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
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary/30 p-4 md:p-12 overflow-x-hidden">
      
      {/* HEADER: Minimalist */}
      <header className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3 mb-2"
          >
            <div className="h-2 w-2 bg-primary rounded-full animate-pulse" />
            <span className="font-mono text-xs text-muted-foreground tracking-[0.2em] uppercase">System Online</span>
          </motion.div>
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-6xl font-black tracking-tighter"
          >
            RALPH<span className="text-primary">LOOP</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-muted-foreground font-mono text-sm mt-2"
          >
            ITERATION 32 // HIGH VELOCITY TEST
          </motion.p>
        </div>

        {/* HUD: Floating Numbers */}
        <div className="flex gap-8 md:gap-12">
          {[
            { label: "SIGNALS", value: stats.total },
            { label: "EXTRACTIONS", value: stats.picks, highlight: true },
            { label: "PENDING", value: stats.pending }
          ].map((stat, i) => (
            <motion.div 
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i }}
              className="text-right"
            >
              <div className="text-[10px] font-mono text-muted-foreground mb-1 tracking-widest">{stat.label}</div>
              <div className={cn("text-3xl font-bold font-mono leading-none", stat.highlight && "text-primary")}>
                {stat.value}
              </div>
            </motion.div>
          ))}
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        
        {/* MAIN FEED */}
        <div className="lg:col-span-8 space-y-8">
          <div className="flex items-center gap-4 border-b border-border/50 pb-4">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="FILTER_STREAM..." 
              className="bg-transparent border-none focus:outline-none text-sm font-mono w-full text-foreground placeholder:text-muted-foreground/50 uppercase tracking-widest"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <div className="space-y-4">
            <AnimatePresence mode='popLayout'>
              {loading ? (
                <motion.div 
                  initial={{ opacity: 0 }} 
                  animate={{ opacity: 1 }} 
                  className="py-20 text-center font-mono text-sm text-muted-foreground"
                >
                  <span className="inline-block animate-spin mr-2">/</span> ESTABLISHING LINK...
                </motion.div>
              ) : filteredData.length === 0 ? (
                 <div className="py-20 text-center font-mono text-sm text-muted-foreground opacity-50">NO SIGNAL DETECTED</div>
              ) : (
                filteredData.map((item, idx) => (
                  <motion.div 
                    key={item.id || idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    layout
                  >
                    <Card className="group border-l-2 border-transparent hover:border-primary pl-4 -ml-4">
                      {/* Header Line */}
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center gap-3">
                          <span className="font-bold text-sm tracking-tight">{item.source}</span>
                          <span className="text-[10px] text-muted-foreground font-mono">{item.date}</span>
                        </div>
                        <Badge variant="outline">{item.expected_picks?.length || 0} PICKS</Badge>
                      </div>

                      {/* Picks Section (Hero) */}
                      {item.expected_picks && item.expected_picks.length > 0 ? (
                        <div className="grid gap-2 mb-3">
                          {item.expected_picks.map((pick, pIdx) => (
                            <div key={pIdx} className="bg-secondary/10 p-3 rounded flex justify-between items-center group-hover:bg-secondary/20 transition-colors">
                              <div>
                                <div className="font-bold text-primary flex items-center gap-2">
                                  {pick.pick}
                                  {pick.odds && <span className="text-xs text-muted-foreground font-mono px-1.5 py-0.5 border border-border rounded">{pick.odds > 0 ? `+${pick.odds}` : pick.odds}</span>}
                                </div>
                                <div className="text-[10px] text-muted-foreground font-mono mt-1 uppercase tracking-wider">
                                  {pick.league} <span className="mx-1">/</span> {pick.type} <span className="mx-1">/</span> {pick.units}U
                                </div>
                              </div>
                              <div className="h-2 w-2 rounded-full bg-yellow-500/50" />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-muted-foreground italic mb-3">No confident picks extracted.</div>
                      )}

                      {/* Controls */}
                      <div className="flex justify-between items-center pt-2">
                         <button 
                           onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                           className="text-[10px] font-mono text-muted-foreground hover:text-foreground flex items-center gap-1 uppercase tracking-widest transition-colors"
                         >
                           {expandedId === item.id ? 'Close Raw' : 'View Raw'} 
                           {expandedId === item.id ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                         </button>
                         <span className="text-[10px] font-mono text-muted-foreground opacity-30">{item.id}</span>
                      </div>

                      {/* Expandable Raw Text */}
                      <AnimatePresence>
                        {expandedId === item.id && (
                          <motion.div 
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-4 p-4 bg-black/40 rounded border border-border/50">
                              <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
                                {item.text}
                              </pre>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </Card>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* SIDEBAR: Analytics */}
        <div className="lg:col-span-4 space-y-8">
           <div className="sticky top-8">
              <h2 className="text-sm font-bold tracking-widest mb-6 flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                NETWORK METRICS
              </h2>
              
              <div className="space-y-8 relative">
                {/* Decorative Line */}
                <div className="absolute left-0 top-2 bottom-2 w-px bg-gradient-to-b from-primary/50 to-transparent" />

                <div className="pl-6 relative">
                  <div className="absolute left-[-4px] top-1.5 h-2 w-2 rounded-full bg-primary border-2 border-background" />
                  <div className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest mb-1">Recall Rate</div>
                  <div className="text-2xl font-bold">94.1%</div>
                  <div className="w-full bg-secondary/30 h-1 mt-2 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: "94.1%" }} className="h-full bg-primary" />
                  </div>
                </div>

                <div className="pl-6 relative">
                  <div className="absolute left-[-4px] top-1.5 h-2 w-2 rounded-full bg-yellow-500 border-2 border-background" />
                  <div className="text-[10px] text-muted-foreground font-mono uppercase tracking-widest mb-1">Precision</div>
                  <div className="text-2xl font-bold">89.5%</div>
                   <div className="w-full bg-secondary/30 h-1 mt-2 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: "89.5%" }} className="h-full bg-yellow-500" />
                  </div>
                </div>

                <div className="pl-6 relative pt-4">
                   <h3 className="text-xs font-bold mb-4">ACTIVE NODES</h3>
                   <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs p-2 bg-secondary/10 rounded border border-border/50">
                        <span className="flex items-center gap-2 font-mono"><Zap className="h-3 w-3 text-green-500" /> Llama 3.1</span>
                        <span className="bg-green-500/10 text-green-500 px-1.5 py-0.5 rounded text-[10px]">ONLINE</span>
                      </div>
                      <div className="flex items-center justify-between text-xs p-2 bg-secondary/10 rounded border border-border/50">
                        <span className="flex items-center gap-2 font-mono"><Radio className="h-3 w-3 text-yellow-500" /> Mistral 7B</span>
                        <span className="bg-yellow-500/10 text-yellow-500 px-1.5 py-0.5 rounded text-[10px]">STANDBY</span>
                      </div>
                   </div>
                </div>

              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
