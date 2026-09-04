interface PendingView {
  readonly templateId: string;
  readonly token: symbol;
}

export class ViewGeneration {
  private readonly pending = new Map<string, PendingView>();

  begin(id: string, templateId: string): symbol {
    const token = Symbol(id);
    this.pending.set(id, { templateId, token });
    return token;
  }

  isPending(id: string, templateId: string): boolean {
    return this.pending.get(id)?.templateId === templateId;
  }

  isCurrent(id: string, token: symbol): boolean {
    return this.pending.get(id)?.token === token;
  }

  complete(id: string, token: symbol): boolean {
    if (!this.isCurrent(id, token)) return false;
    this.pending.delete(id);
    return true;
  }

  cancel(id: string): void {
    this.pending.delete(id);
  }

  cancelMissing(validIds: ReadonlySet<string>): void {
    for (const id of this.pending.keys()) {
      if (!validIds.has(id)) this.pending.delete(id);
    }
  }

  clear(): void {
    this.pending.clear();
  }
}
