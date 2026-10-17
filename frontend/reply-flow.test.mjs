import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const [app, commentList, commentForm, serializers] = await Promise.all([
  readFile(new URL('./src/App.vue', import.meta.url), 'utf8'),
  readFile(new URL('./src/components/CommentList.vue', import.meta.url), 'utf8'),
  readFile(new URL('./src/components/CommentForm.vue', import.meta.url), 'utf8'),
  readFile(new URL('../backend/comments/serializers.py', import.meta.url), 'utf8')
])

const checks = [
  ['form emits its FormData', /this\.\$emit\('commentCreated', formData\)/.test(commentForm)],
  ['form provides textarea and vertical attachment actions', /<textarea\b[\s\S]*?<div class="comment-form-controls">[\s\S]*?Add text file[\s\S]*?Add image/.test(commentForm)],
  ['root comment button toggles a form before the comment list', /comments-toolbar[\s\S]*?@click="showRootCommentForm = !showRootCommentForm"/.test(app) && /<CommentForm[\s\S]*?v-if="token && showRootCommentForm"[\s\S]*?<CommentList/.test(app)],
  ['root comment form is not rendered at the page bottom', !/<CommentForm v-if="token" @commentCreated="handleCommentCreated"\s*\/>/.test(app)],
  ['root comment form closes after a successful post', /this\.showRootCommentForm = false/.test(app)],
  ['authentication controls align to the right', /\.header-content\s*\{[^}]*width:\s*100%/.test(app) && /\.auth-actions\s*\{[^}]*margin-left:\s*auto/.test(app) && /\.user-info\s*\{[^}]*margin-left:\s*auto/.test(app)],
  ['comment list forwards its form event', /<CommentForm\b[^>]*@commentCreated="handleCommentCreated"/.test(commentList)],
  ['nested replies forward their events', /<CommentList\b[\s\S]*?@commentCreated="handleCommentCreated"/.test(commentList)],
  ['App handles the reply event', /<CommentList\b[\s\S]*?@commentCreated="handleCommentCreated"/.test(app)],
  ['App POSTs the submitted comment', /\/api\/comments\//.test(app)],
  ['WebSocket comments include their root comment ID', /def get_root_id\(self, obj\):\s+return obj\.get_root\(\)\.id/.test(serializers)],
  ['root comments and replies use separate buffers', /commentData\.parent == null[\s\S]*?bufferedComments\.push\(commentData\)[\s\S]*?commentData\.root_id != null[\s\S]*?bufferedReplies\[rootId\]/.test(app)],
  ['reply counter reloads and replaces the cached tree', /New replies \(\{\{ newReplyCounts\[comment\.id\] \}\}\)/.test(commentList) && /this\.setLoadedChildren\(commentId, childrenData\)/.test(commentList)],
  ['successful reply creation notifies its parent ID', /const parentId = formData\.get\('parent'\)[\s\S]*?this\.lastCreatedReply = \{ parentId: Number\(parentId\), commentId: data\.id \}/.test(app)],
  ['reply form closes only when its parent reply has been created', /lastCreatedReply\(reply\)[\s\S]*?(reply\.parentId\s*===\s*Number\(this\.showReplyForm\)|Number\(this\.showReplyForm\)\s*===\s*reply\.parentId)[\s\S]*?this\.showReplyForm\s*=\s*null/.test(commentList)],
  ['comment author avatar is rendered with lazy browser caching and a download link', /comment\.avatar[\s\S]*?:href="getDownloadUrl\(comment\.avatar\)"[\s\S]*?:src="getPublicMediaUrl\(comment\.avatar\)"[\s\S]*?loading="lazy"/.test(commentList)],
  ['comment serializers include author avatar', /"avatar"/.test(serializers)],
  ['registration loads and displays a CAPTCHA challenge', /fetch\('\/api\/captcha\/'\)/.test(app) && /register\.captchaQuestion/.test(app)],
  ['registration sends CAPTCHA key and answer', /formData\.append\(['"]captcha_key['"],\s*this\.register\.captchaKey\)/.test(app) && /formData\.append\(['"]captcha_value['"],\s*this\.register\.captchaAnswer\)/.test(app)],
  ['registration displays API validation errors and requests a fresh challenge', /this\.registerError = this\.getRegistrationErrorMessage\(err\)[\s\S]*?this\.loadCaptcha\(\)/.test(app) && /getRegistrationErrorMessage\(error\)[\s\S]*?Object\.entries\(error\)/.test(app)],
  ['successful registration automatically obtains and stores JWT tokens', /Registration successful:[\s\S]*?fetch\('\/api\/user\/token\/'[\s\S]*?body: JSON\.stringify\(\{ username, password \}\)[\s\S]*?localStorage\.setItem\('access_token', tokens\.access\)[\s\S]*?localStorage\.setItem\('refresh_token', tokens\.refresh\)/.test(app)],
  ['registration stays complete if automatic login fails', /Registration succeeded, but automatic login failed\. Please log in\./.test(app)]
]
const failures = checks.filter(([, passed]) => !passed).map(([name]) => name)
if (failures.length) {
  console.error(`FAIL: ${failures.join('; ')}`)
  process.exitCode = 1
} else {
  console.log('PASS: reply submission and per-root reply notifications are wired')
}
