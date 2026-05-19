export interface Flags {
	debug: boolean;
	calibration: boolean;
}

export function getFlags(): Flags {
	const debugCheckbox = document.getElementById(
		'debug-flag'
	) as HTMLInputElement | null;
	const calibrationCheckbox = document.getElementById(
		'calibration-flag'
	) as HTMLInputElement | null;

	return {
		debug: debugCheckbox ? debugCheckbox.checked : false,
		calibration: calibrationCheckbox ? calibrationCheckbox.checked : false,
	};
}
