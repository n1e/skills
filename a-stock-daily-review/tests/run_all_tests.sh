#!/bin/bash
echo "===== 运行所有测试 =====
"
for f in test_*.py; do
    echo ">>> 运行 $f"
    python3 "$f"
    echo ""
done

