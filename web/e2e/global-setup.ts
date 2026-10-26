import { execFileSync } from 'node:child_process';
import { AUTH, PROJECT } from './helpers';

// Emulatori puliti e dati di prova a ogni esecuzione.
export default async function globalSetup() {
	await fetch(`http://127.0.0.1:8080/emulator/v1/projects/${PROJECT}/databases/(default)/documents`, { method: 'DELETE' });
	await fetch(`${AUTH}/emulator/v1/projects/${PROJECT}/accounts`, { method: 'DELETE' });
	execFileSync(process.execPath, ['scripts/seed-emulator.mjs'], { stdio: 'inherit' });
}
