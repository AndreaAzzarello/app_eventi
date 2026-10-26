// Messaggi brevi e non bloccanti, annunciati agli screen reader dal contenitore aria-live.
export interface Toast {
	id: number;
	text: string;
	action?: { label: string; href: string };
}

let next = 1;
export const toasts = $state<Toast[]>([]);

export function toast(text: string, action?: Toast['action'], ms = 6000) {
	const t = { id: next++, text, action };
	toasts.push(t);
	setTimeout(() => dismiss(t.id), ms);
}

export function dismiss(id: number) {
	const i = toasts.findIndex((t) => t.id === id);
	if (i >= 0) toasts.splice(i, 1);
}
