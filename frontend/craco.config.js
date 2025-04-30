// Last reviewed: 2025-04-30 11:17:29 UTC (User: TeeksssYüksek)
const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
const CompressionPlugin = require('compression-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const path = require('path');

module.exports = {
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    plugins: [
      // Bundle analiz için plugin (npm run build:analyze ile kullan)
      ...(process.env.ANALYZE ? [new BundleAnalyzerPlugin()] : []),
      // Gzip sıkıştırma
      new CompressionPlugin({
        filename: '[path][base].gz',
        algorithm: 'gzip',
        test: /\.(js|css|html|svg)$/,
        threshold: 10240, // Yalnızca 10KB'dan büyük dosyaları sıkıştır
        minRatio: 0.8, // Minimum sıkıştırma oranı
      }),
      // Brotli sıkıştırma
      new CompressionPlugin({
        filename: '[path][base].br',
        algorithm: 'brotliCompress',
        test: /\.(js|css|html|svg)$/,
        threshold: 10240,
        minRatio: 0.8,
      }),
    ],
    configure: (webpackConfig) => {
      // Dosya boyut uyarı limitini arttır
      webpackConfig.performance = {
        hints: 'warning',
        maxAssetSize: 512000, // 500KB
        maxEntrypointSize: 512000, // 500KB
      };
      
      // Terser optimizasyon ayarları
      webpackConfig.optimization.minimizer = [
        new TerserPlugin({
          terserOptions: {
            compress: {
              drop_console: process.env.NODE_ENV === 'production', // Production'da console.log'ları kaldır
              drop_debugger: true,
              pure_funcs: process.env.NODE_ENV === 'production' ? ['console.log', 'console.debug', 'console.info'] : [],
            },
            output: {
              comments: false, // Yorum satırlarını kaldır
            },
            mangle: true,
          },
          extractComments: false,
        }),
      ];
      
      // Code splitting ayarları
      webpackConfig.optimization.splitChunks = {
        chunks: 'all',
        maxInitialRequests: 20, // Max ilk istek sayısı
        minSize: 20000, // Min chunk boyutu (byte)
        maxSize: 244000, // Max chunk boyutu (244KB)
        cacheGroups: {
          defaultVendors: {
            test: /[\\/]node_modules[\\/]/,
            priority: -10,
            reuseExistingChunk: true,
            name(module) {
              // node_modules'dan paketler için ayrı chunk'lar oluştur
              const packageName = module.context.match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/)[1];
              // bazı paketler için özel ayarlar
              if (['react', 'react-dom'].includes(packageName)) {
                return 'core-vendors';
              } else if (['@mui', '@material-ui', 'react-bootstrap'].some(pkg => packageName.startsWith(pkg))) {
                return 'ui-vendors';
              } else if (['lodash', 'moment', 'date-fns'].includes(packageName)) {
                return 'util-vendors';
              }
              return `vendor-${packageName.replace('@', '')}`;
            },
          },
          default: {
            minChunks: 2,
            priority: -20,
            reuseExistingChunk: true,
          },
        },
      };
      
      return webpackConfig;
    },
  },
  jest: {
    configure: {
      moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
      },
    },
  },
  babel: {
    plugins: [
      // Bileşen içeri aktarmalarını optimize et
      [
        'babel-plugin-transform-imports',
        {
          'react-bootstrap': {
            transform: 'react-bootstrap/lib/${member}',
            preventFullImport: true,
          },
          lodash: {
            transform: 'lodash/${member}',
            preventFullImport: true,
          },
        }
      ],
      // Cherry-pick lodash fonksiyonları
      'lodash',
    ],
  },
  // PostCSS ile CSS optimizasyonu
  style: {
    postcss: {
      plugins: [
        require('autoprefixer'),
        require('cssnano')({
          preset: ['default', {
            discardComments: { removeAll: true },
            minifyFontValues: { removeQuotes: false },
          }],
        }),
      ],
    },
  },
};