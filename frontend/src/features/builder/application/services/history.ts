export interface Command {
  execute(): void;
  undo(): void;
}

export class HistoryManager {
  private past: Command[] = [];
  private future: Command[] = [];

  public execute(command: Command): void {
    command.execute();
    this.past.push(command);
    this.future = []; // Clear redo stack
  }

  public undo(): void {
    const command = this.past.pop();
    if (command) {
      command.undo();
      this.future.push(command);
    }
  }

  public redo(): void {
    const command = this.future.pop();
    if (command) {
      command.execute();
      this.past.push(command);
    }
  }

  public canUndo(): boolean {
    return this.past.length > 0;
  }

  public canRedo(): boolean {
    return this.future.length > 0;
  }

  public clear(): void {
    this.past = [];
    this.future = [];
  }
}
