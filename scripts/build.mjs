import webpack from 'webpack'
import { mkdirSync, cpSync } from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '..')

await new Promise((resolve, reject) => webpack({
    mode: 'production', entry: path.join(root, 'src/files.js'),
    output: { path: path.join(root, 'js'), filename: 'cadviewer-files.js', clean: false },
    devtool: false, optimization: { minimize: true },
    performance: { hints: 'warning' },
}, (error, stats) => {
    if (error || stats.hasErrors()) reject(error || new Error(stats.toString('errors-only')))
    else { console.log(stats.toString({ all: false, assets: true, warnings: true })); resolve() }
}))

const destination = path.join(root, 'assets/viewer')
mkdirSync(destination, { recursive: true })
for (const name of ['frame.js', 'frame.css']) cpSync(path.join(root, 'src', name), path.join(destination, name))
console.log('Packaged free SVG viewer; no commercial SDK')
