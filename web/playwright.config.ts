import { defineConfig, devices } from '@playwright/test';

// Richiede gli emulatori Firebase attivi (npm run test:e2e li avvia da sé con emulators:exec).
export default defineConfig({
	testDir: 'e2e',
	fullyParallel: false,
	workers: 1,
	retries: 0,
	timeout: 60_000,
	expect: { timeout: 10_000 },
	reporter: [['list']],
	globalSetup: './e2e/global-setup.ts',
	use: {
		baseURL: 'http://localhost:4300',
		locale: 'it-IT',
		timezoneId: 'Europe/Rome',
		trace: 'retain-on-failure'
	},
	projects: [
		{ name: 'mobile', use: { ...devices['Pixel 7'] }, testIgnore: /desktop\.spec\.ts/ },
		{ name: 'desktop', use: { ...devices['Desktop Chrome'] }, testMatch: /desktop\.spec\.ts/ }
	],
	webServer: {
		command: 'npm run build && npx vite preview --port 4300 --strictPort',
		port: 4300,
		reuseExistingServer: !process.env.CI,
		timeout: 180_000
	}
});
