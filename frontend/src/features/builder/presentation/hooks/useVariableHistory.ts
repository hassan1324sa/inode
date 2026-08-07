import { useState, useEffect } from "react";
import type { ExecutionEvent } from "./useExecutionStream";

export interface VariableChange {
  variableName: string;
  previousValue: any;
  currentValue: any;
  nodeId?: string;
  sequence: number;
  timestamp: number;
}

export function useVariableHistory(events: ExecutionEvent[]) {
  const [variableHistory, setVariableHistory] = useState<Record<string, VariableChange[]>>({});

  useEffect(() => {
    const history: Record<string, VariableChange[]> = {};
    events.forEach((event) => {
      if (event.event_type === "VariableChanged") {
        const name = event.payload.variable_name;
        if (name) {
          if (!history[name]) {
            history[name] = [];
          }
          history[name].push({
            variableName: name,
            previousValue: event.payload.previous_value,
            currentValue: event.payload.current_value,
            nodeId: event.node_id,
            sequence: event.sequence,
            timestamp: event.timestamp
          });
        }
      }
    });
    setVariableHistory(history);
  }, [events]);

  const getVariableValueAtStep = (name: string, upToSequence: number) => {
    const changes = variableHistory[name] || [];
    let currentVal = null;
    for (const change of changes) {
      if (change.sequence > upToSequence) break;
      currentVal = change.currentValue;
    }
    return currentVal;
  };

  return { variableHistory, getVariableValueAtStep };
}
