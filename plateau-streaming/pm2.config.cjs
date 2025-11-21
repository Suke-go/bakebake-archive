const path = require('node:path');

module.exports = {
  apps: [
    {
      name: 'plateau-streaming',
      cwd: __dirname,
      script: path.resolve(__dirname, 'server.mjs'),
      node_args: '--enable-source-maps',
      env: {
        PORT: process.env.PORT || '18080',
        DATA_DIR: process.env.DATA_DIR || path.resolve(__dirname, 'data'),
      },
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      instances: 1,
    },
  ],
};

