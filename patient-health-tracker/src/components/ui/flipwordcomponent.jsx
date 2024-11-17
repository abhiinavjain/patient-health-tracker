import React from "react";
import { FlipWords } from "./flip-words";


export function FlipWordsDemo() {
  const words = ["Powered  ", "Driven", "Optimized", "Engineered"];

  return (
    (<div >
      <div
        className="text-6xl font-bold mb-4 text-[#04395E]">
        AI 
         <FlipWords words={words}/><br/>
         Disease Prediction Model 
      </div>
    </div>)
  );
}
