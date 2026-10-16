# Review package

BASE_SHA: 0000000000000000000000000000000000000001
HEAD_SHA: 0000000000000000000000000000000000000002

## Commits

0000000000000000000000000000000000000002 feat(canary): word count helper with tests

## Diff stat

 canary/test_wc.py | 21 +++++++++++++++++++++
 canary/wc.py      | 10 ++++++++++
 2 files changed, 31 insertions(+)

## Diff

```diff
diff --git a/canary/wc.py b/canary/wc.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/canary/wc.py
@@ -0,0 +1,10 @@
+"""Word count helper."""
+
+
+def _tokens(text):
+    return [part for part in text.split(" ") if part]
+
+
+def word_count(text):
+    """Return the number of words in text."""
+    return len(_tokens(text))
diff --git a/canary/test_wc.py b/canary/test_wc.py
new file mode 100644
index 0000000..2222222
--- /dev/null
+++ b/canary/test_wc.py
@@ -0,0 +1,21 @@
+from canary import wc
+
+SAMPLE = "the quick  brown fox\tjumps"
+
+
+def test_word_count_simple():
+    assert wc.word_count("a b  c") == 3
+
+
+def test_tokens_drop_empty_parts():
+    assert wc._tokens("a  b") == ["a", "b"]
+
+
+def test_word_count_sample():
+    expected = len(wc._tokens(SAMPLE))
+    assert wc.word_count(SAMPLE) == expected
+
+
+def test_word_count_empty():
+    assert wc.word_count("") == 0
```
