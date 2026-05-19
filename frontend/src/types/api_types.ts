export type Mode = 'minifig' | 'set';

export interface LabelRequest {
	ids: string[];
	debug: boolean;
	calibration: boolean;
}

export interface ItemWarning {
	id: string;
	reason: string;
	mean_lstar: number | null;
}

export interface HealthResponse {
	ok: boolean;
	config_present: boolean;
	vendor_commit: string;
	offline_fixture_mode: boolean;
}

export interface CredentialsMissingResponse {
	error: 'credentials_missing';
	expected_path: string;
}

export type StreamEvent =
	| { type: 'start'; mode: 'minifig' | 'set'; count: number }
	| { type: 'item_start'; id: string; index: number; total: number }
	| { type: 'item_done'; id: string; name: string; warning: string | null }
	| { type: 'image_downloaded'; id: string; kind: 'minifig' | 'set' }
	| { type: 'image_processed'; id: string; kind: 'minifig' | 'set' }
	| { type: 'render_start' }
	| { type: 'done'; pdf_b64: string; warnings: ItemWarning[] }
	| { type: 'error'; error: string; expected_path?: string; message?: string };
