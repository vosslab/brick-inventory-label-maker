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
