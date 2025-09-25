// CommonJS Vite config to harden dev server and make build output predictable.
// Using module.exports avoids importing 'vite' at config-parse time so a transient
// npx installation of the CLI can run the build without a local dependency.
module.exports = {
  server: {
    host: '127.0.0.1', // bind to localhost only
    strictPort: true,  // fail if port is in use
    port: 5174
    ,
    // Proxy API calls to local backend during dev so frontend can run on 5174
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
}

// Use frontend_temp/index.html as the build entry
module.exports.build.rollupOptions = {
  input: './frontend_temp/index.html'
}
