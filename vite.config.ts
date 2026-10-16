import { defineConfig, loadEnv } from 'vite';
import { createHandler } from './server/rewrite.mjs';
export default defineConfig(({mode}) => {
  // Server closure only. Never expose these through define or VITE_ variables.
  const env={...loadEnv(mode,process.cwd(),''),...process.env};
  const handler=createHandler({env});
  const mount = (server: any) => {server.middlewares.use('/api/rewrite',handler);};
  return {plugins:[{name:'local-rewrite-api',configureServer:mount,configurePreviewServer:mount}]};
});
