import React from 'react';
import AppRouter from './AppRouter';
import DiseasePrediction from './components/DiseasePrediction';


import { motion } from "framer-motion";
import { AuroraBackground } from './components/ui/aurora-background';
import { FloatingDockDemo } from './components/FloatingDockDemo';
import { FloatingDock } from './components/ui/floating-dock';


function App() {
  return (
    <div className="App">

  
  <AuroraBackground>
      <motion.div
        initial={{ opacity: 0.0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{
          delay: 0.3,
          duration: 0.8,
          ease: "easeInOut",
        }}
        className="relative flex flex-col gap-4 items-center justify-center px-4"
      >
      <AppRouter />
      
     
        
    </motion.div>
    </AuroraBackground>
     
 
    </div>
  );
}

export default App;
