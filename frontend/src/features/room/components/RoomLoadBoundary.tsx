import { Component, Suspense, type ReactNode } from "react";

import { LazyRoomAppView } from "./LazyRoomAppView";
import type { RoomAppViewProps } from "./RoomAppView";

interface RoomLoadBoundaryProps extends RoomAppViewProps {
  onExitToClassic: () => void;
}

function RoomLoading({ onExitToClassic }: { onExitToClassic: () => void }) {
  return (
    <main className="room-fallback" aria-live="polite">
      <p className="room-fallback__title">Открываем комнату…</p>
      <button type="button" className="room-fallback__back" onClick={onExitToClassic}>
        Вернуться в старый UI
      </button>
    </main>
  );
}

interface RoomErrorBoundaryState {
  failed: boolean;
}

/** A failed lazy chunk must never trap the user: classic stays one tap away. */
class RoomErrorBoundary extends Component<
  { children: ReactNode; onExitToClassic: () => void },
  RoomErrorBoundaryState
> {
  state: RoomErrorBoundaryState = { failed: false };

  static getDerivedStateFromError(): RoomErrorBoundaryState {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="room-fallback" role="alert">
          <p className="room-fallback__title">Не получилось открыть комнату</p>
          <p className="room-fallback__note">Можно остаться в привычном дизайне.</p>
          <button type="button" className="room-fallback__back" onClick={this.props.onExitToClassic}>
            Вернуться в старый UI
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}

export function RoomLoadBoundary({ onExitToClassic, ...roomProps }: RoomLoadBoundaryProps) {
  return (
    <RoomErrorBoundary onExitToClassic={onExitToClassic}>
      <Suspense fallback={<RoomLoading onExitToClassic={onExitToClassic} />}>
        <LazyRoomAppView {...roomProps} />
      </Suspense>
    </RoomErrorBoundary>
  );
}
