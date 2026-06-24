# SDD Progress Ledger

## 2026-06-21: 企微推送从 SCF 迁移到 Gitee Go (v2)

| Task | 状态 | 备注 |
|------|------|------|
| Gitee-1 | ✅ complete | .gitee-ci.yml 创建，commit ff5a959 |
| Gitee-5 | ✅ complete | 标记 GitHub Actions 废弃，commit 2e2d765 |
| Task 4 (v1) | ✅ complete | scf/grant_perm.py 标记废弃，commit 413c38d |
| Task 5 (v1) | ✅ complete | 本地推送通道验证通过 |
| Gitee-2 | ⏳ 等待用户 | 需在 Gitee UI 配置私密变量 |
| Gitee-3 | 🔒 阻塞 | 依赖 Gitee-2 |
| Gitee-4 | 🔒 阻塞 | 依赖 Gitee-3 |
Task 2: complete (commits 289fb5a..7458a43, review clean)
Task 3: complete (commits 7458a43..0635c8b, review clean)
Task 4: complete (commits 0635c8b..122f4fc, review: 2 Minor)
Task 5: complete (commits 122f4fc..4435775, review: 3 Minor)
Task 6: complete (commits 4435775..6aaf513, review clean)
Task 7: complete (commits 6aaf513..fd4f747, 1 fix cycle, review clean)
Task 8: complete (commits fd4f747..d6e227d, integration test pass, 1 bug fix, review clean)
Task 9: complete (cleanup done, final commit f5a16b6)
Final fix: complete (commit 008e7a8, 3 must-fix items resolved)
