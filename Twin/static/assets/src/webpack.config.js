const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
    entry: './index.js',
    output: {
        filename: 'js/bundle.js',
        path: path.resolve(__dirname, '../dist'),
        clean: true, // Cleans `dist/` before each build
    },
    module: {
        rules: [
            // Javascripts
            {
                test: /\.js$/,
                loader: "babel-loader",
                options: {
                    presets: ["@babel/preset-env"],
                },
            },
            // SCSS, SASS, and CSS
            {
                test: /\.(sa|sc|c)ss$/, // Handle SCSS, SASS, and CSS files
                use: [
                    MiniCssExtractPlugin.loader, // Extracts CSS into separate file
                    'css-loader', // Resolves CSS imports
                    'sass-loader', // Compiles SCSS to CSS
                ],
            },
            // Fonts
            {
                test: /\.(ttf|otf|eot|woff(2)?)(\?[a-z0-9]+)?$/,
                type: "asset/resource",
                generator: {
                    filename: "fonts/modules/[path][name][ext]", // Saves in `dist/fonts/`
                },
            },
            // Images
            {
                test: /\.(gif|png|jpe?g|ico|svg)$/,
                type: "asset/resource",
                generator: {
                    filename: "media/modules/[path][name][ext]", // Saves images in `dist/media/`
                },
            },
        ],
    },
    plugins: [
        new MiniCssExtractPlugin({
            // Saves extracted CSS as styles.css
            filename: 'css/bundle.css',
        }),
        new CopyWebpackPlugin({
            patterns: [
                // Copy all custom CSS files from `src/css/` to `dist/css/`
                {
                    from: path.resolve(__dirname, 'css'),
                    to: path.resolve(__dirname, '../dist/css/')
                },

                // Copy all custom JS files from `src/js/` to `dist/js/`
                {
                    from: path.resolve(__dirname, 'js'),
                    to: path.resolve(__dirname, '../dist/js/')
                },
                // Copy all custom media files
                {
                    from: path.resolve(__dirname, 'media'),
                    to: path.resolve(__dirname, '../dist/media/')
                },
                // Copy all custom fonts
                {
                    from: path.resolve(__dirname, 'fonts'),
                    to: path.resolve(__dirname, '../dist/fonts/'),
                    noErrorOnMissing: true // Allows empty or missing
                },
            ],
        }),
    ],
};