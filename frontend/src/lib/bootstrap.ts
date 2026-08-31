export type AppPhase = "loading" | "ready" | "session-error" | "storage-error";

interface AppBootstrapSteps {
  openSession: () => Promise<unknown>;
  ensureKey: () => Promise<unknown>;
}

export function createAppBootstrap(
  steps: AppBootstrapSteps,
  onPhase: (phase: AppPhase) => void,
): { connect: () => Promise<void> } {
  return {
    async connect() {
      onPhase("loading");
      try {
        await steps.openSession();
      } catch {
        onPhase("session-error");
        return;
      }
      try {
        await steps.ensureKey();
      } catch {
        onPhase("storage-error");
        return;
      }
      onPhase("ready");
    },
  };
}
