#!/usr/bin/env node
/**
 * 构建产物同步脚本（跨平台，Node 实现）。
 *
 * 用法：node scripts/sync-build.mjs <构建输出目录> <静态托管目录>
 *
 * 作用：把 vite 构建输出（dist）同步到 Caddy 静态托管目录。
 * 顺序刻意设计为「先写新文件、后删旧文件」：
 *   1. 先把新产物（index.html 与新 hash 的 assets）复制进目标目录；
 *   2. 再清理目标目录中已不在新产物里的旧文件（保留宽限期内的，见 GRACE_MS）。
 * 这样在线用户即使仍在使用旧的 index.html，也能加载完旧 chunk，
 * 避免「构建先清空目录、再写新文件」窗口期内的资源 404。
 */
import { cpSync, existsSync, readdirSync, rmSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

// 旧产物保留期：发版时页面已打开的用户，之后仍可能按需加载旧 chunk
// （SPA 路由懒加载）。立刻删除会让这些请求 404，页面直接报错；
// 保留一段时间后，过期文件会在后续发版时自动清理，磁盘占用有上限。
const GRACE_MS = 7 * 24 * 60 * 60 * 1000

const [srcArg, destArg] = process.argv.slice(2)
if (!srcArg || !destArg) {
  console.error('用法: node scripts/sync-build.mjs <构建输出目录> <静态托管目录>')
  process.exit(1)
}

const src = resolve(process.cwd(), srcArg)
const dest = resolve(process.cwd(), destArg)

if (!existsSync(src)) {
  console.error(`未找到构建产物目录: ${src}`)
  process.exit(1)
}

// 1. 先复制新产物：写入新文件、覆盖同名旧文件。
cpSync(src, dest, { recursive: true })

// 2. 收集新产物中的文件相对路径集合，用于判定哪些旧文件需要清理。
const keep = new Set()
;(function collect(dir) {
  for (const name of readdirSync(dir)) {
    const abs = join(dir, name)
    if (statSync(abs).isDirectory()) {
      collect(abs)
    } else {
      keep.add(relative(src, abs))
    }
  }
})(src)

// 3. 后清理目标目录中已不在新产物里的旧文件；仍在宽限期内的先留着。
// cpSync 未保留时间戳，被复制的文件时间为当前时间，因此本版产物必定在宽限期内、不会被误删。
let removed = 0
let kept = 0
;(function clean(dir) {
  for (const name of readdirSync(dir)) {
    const abs = join(dir, name)
    const stat = statSync(abs)
    if (stat.isDirectory()) {
      clean(abs)
    } else if (!keep.has(relative(dest, abs))) {
      if (Date.now() - stat.mtimeMs < GRACE_MS) {
        kept += 1
      } else {
        rmSync(abs)
        removed += 1
      }
    }
  }
})(dest)

console.log(`同步完成: ${src} -> ${dest}（清理旧文件 ${removed} 个，宽限期内保留 ${kept} 个）`)
