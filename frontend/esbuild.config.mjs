#!/usr/bin/env node

import esbuild from 'esbuild';
import fs from 'fs';
import path from 'path';

const srcDir = path.join(process.cwd(), 'src');
const distDir = path.join(process.cwd(), 'dist');

// Ensure dist directory exists
if (!fs.existsSync(distDir)) {
	fs.mkdirSync(distDir, { recursive: true });
}

async function build() {
	try {
		// Bundle TypeScript
		await esbuild.build({
			entryPoints: [path.join(srcDir, 'init.ts')],
			outfile: path.join(distDir, 'app.js'),
			bundle: true,
			format: 'esm',
			target: 'es2022',
			sourcemap: 'inline',
			minify: false,
			treeShaking: true,
		});

		// Copy HTML and CSS
		fs.copyFileSync(
			path.join(process.cwd(), 'index.html'),
			path.join(distDir, 'index.html')
		);
		fs.copyFileSync(
			path.join(process.cwd(), 'style.css'),
			path.join(distDir, 'style.css')
		);

		console.log('frontend build OK -> frontend/dist/');
	} catch (error) {
		console.error('esbuild failed:', error);
		process.exit(1);
	}
}

build();
