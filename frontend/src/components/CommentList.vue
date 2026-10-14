<template>
  <div class="comment-table-wrapper">
    <table class="comment-table">
      <thead>
        <tr>
          <th scope="col">Author</th>
          <th scope="col">Date</th>
          <th scope="col">Comment</th>
          <th scope="col">Image</th>
          <th scope="col">File</th>
          <th scope="col">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="comment in comments" :key="comment.id">
          <tr>
            <td>
              <div class="comment-author">
                <a
                  v-if="comment.avatar"
                  class="author-avatar-link"
                  :href="getDownloadUrl(comment.avatar)"
                  :download="getFileName(comment.avatar)"
                  :aria-label="`Download avatar for ${comment.author}`"
                >
                  <img
                    class="author-avatar"
                    :src="getPublicMediaUrl(comment.avatar)"
                    :alt="`${comment.author}'s avatar`"
                    width="36"
                    height="36"
                    loading="lazy"
                    decoding="async"
                  />
                </a>
                <span>{{ comment.author }}</span>
              </div>
            </td>
            <td>{{ new Date(comment.created_at).toLocaleString() }}</td>
            <td class="comment-content" v-html="comment.content"></td>
            <td>
              <a
                v-if="comment.image"
                :href="getDownloadUrl(comment.image)"
                :download="getFileName(comment.image)"
                :aria-label="`Download image for comment ${comment.id}`"
              >
                <img
                  class="comment-thumbnail"
                  :src="getPublicMediaUrl(comment.image)"
                  :alt="`Image for comment ${comment.id}`"
                  width="96"
                  height="72"
                  loading="lazy"
                  decoding="async"
                />
              </a>
              <span v-else class="empty-value">—</span>
            </td>
            <td>
              <a
                v-if="comment.file"
                :href="getDownloadUrl(comment.file)"
                :download="getFileName(comment.file)"
                class="file-download"
              >
                Download
              </a>
              <span v-else class="empty-value">—</span>
            </td>
            <td class="comment-actions">
              <button type="button" @click="toggleReplyForm(comment.id)">Reply</button>
              <button type="button" class="expand-btn" @click="toggleExpand(comment)">
                {{ expanded[comment.id] ? 'Collapse' : 'Expand' }}
              </button>
              <button
                v-if="newReplyCounts[comment.id]"
                type="button"
                class="new-replies-btn"
                @click="refreshReplies(comment.id)"
              >
                New replies ({{ newReplyCounts[comment.id] }})
              </button>
            </td>
          </tr>
          <tr v-if="showReplyForm === comment.id && token">
            <td colspan="6">
              <div class="reply-form">
                <CommentForm :parentId="comment.id" @commentCreated="handleCommentCreated" />
              </div>
            </td>
          </tr>
          <tr v-if="expanded[comment.id]">
            <td colspan="6" class="replies-cell">
              <CommentList
                v-if="hasLoadedChildren(comment.id) && getCommentChildren(comment.id).length"
                :comments="getCommentChildren(comment.id)"
                :updateComment="updateComment"
                :setLoadedChildren="setLoadedChildren"
                :getCommentChildren="getCommentChildren"
                :hasLoadedChildren="hasLoadedChildren"
                :token="token"
                :newReplyCounts="newReplyCounts"
                :clearReplyNotifications="clearReplyNotifications"
                :lastCreatedReply="lastCreatedReply"
                @commentCreated="handleCommentCreated"
              />
              <p v-else-if="hasLoadedChildren(comment.id)" class="empty-replies">
                No comments yet.
              </p>
            </td>
          </tr>
        </template>
        <tr v-if="comments.length === 0">
          <td colspan="6" class="empty-list">No comments yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import CommentForm from './CommentForm.vue'

export default {
  name: 'CommentList',
  components: {
    CommentForm
  },
  props: {
    comments: {
      type: Array,
      required: true
    },
    updateComment: {
      type: Function,
      required: true
    },
    setLoadedChildren: {
      type: Function,
      required: true
    },
    hasLoadedChildren: {
      type: Function,
      required: true
    },
    getCommentChildren: {
      type: Function,
      required: true
    },
    token: {
      type: String,
      required: true
    },
    newReplyCounts: {
      type: Object,
      default: () => ({})
    },
    clearReplyNotifications: {
      type: Function,
      required: true
    },
    lastCreatedReply: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      showReplyForm: null,
      expanded: {},
      loadingReplies: {}
    }
  },
  watch: {
    comments() {
      this.expanded = {}
    },
    lastCreatedReply(reply) {
      if (reply && reply.parentId === Number(this.showReplyForm)) {
        this.showReplyForm = null
      }
    }
  },
  methods: {
    toggleReplyForm(commentId) {
      this.showReplyForm = this.showReplyForm === commentId ? null : commentId
    },
    toggleExpand(comment) {
      const commentId = comment?.id
      if (!commentId) {
        console.error('commentId is undefined or null')
        return
      }
      if (this.expanded[commentId]) {
        this.expanded[commentId] = false
        return
      }
      if (!this.hasLoadedChildren(commentId) || this.newReplyCounts[commentId]) {
        this.refreshReplies(commentId)
      } else {
        this.expanded[commentId] = true
      }
    },
    refreshReplies(commentId) {
      if (this.loadingReplies[commentId]) return
      this.loadingReplies[commentId] = true
      fetch(`/api/comments/${commentId}/tree/`)
        .then(response => {
          if (!response.ok) {
            throw new Error('Network response was not ok')
          }
          return response.json()
        })
        .then(apiTreeData => {
          const childrenData = (apiTreeData.replies || [])
            .map(reply => this.convertApiTreeToInternalFormat(reply))
          this.setLoadedChildren(commentId, childrenData)
          this.expanded[commentId] = true
          this.clearReplyNotifications(commentId, childrenData)
        })
        .catch(error => {
          console.error('Error fetching comment tree:', error)
        })
        .finally(() => {
          this.loadingReplies[commentId] = false
        })
    },
    convertApiTreeToInternalFormat(apiComment) {
      if (!apiComment) return null
      const { replies, ...commentWithoutReplies } = apiComment
      const commentWithChildren = { ...commentWithoutReplies, children: [] }
      if (Array.isArray(replies)) {
        commentWithChildren.children = replies.map(reply => this.convertApiTreeToInternalFormat(reply))
      }
      return commentWithChildren
    },
    getPublicMediaUrl(mediaUrl) {
      const url = new URL(mediaUrl, window.location.origin)
      const s3Path = '/storage/v1/s3/'
      if (url.pathname.includes(s3Path)) {
        url.pathname = url.pathname.replace(s3Path, '/storage/v1/object/public/')
        url.hostname = url.hostname.replace('.storage.supabase.co', '.supabase.co')
      }
      return url.toString()
    },
    getFileName(fileUrl) {
      const path = new URL(fileUrl, window.location.origin).pathname
      return decodeURIComponent(path.substring(path.lastIndexOf('/') + 1)) || 'comment-file'
    },
    getDownloadUrl(mediaUrl) {
      const url = new URL(this.getPublicMediaUrl(mediaUrl))
      url.searchParams.set('download', this.getFileName(mediaUrl))
      return url.toString()
    },
    handleCommentCreated(comment) {
      this.$emit('commentCreated', comment)
    }
  }
}
</script>

<style scoped>
.comment-table-wrapper {
  width: 100%;
  overflow-x: auto;
  margin-bottom: 16px;
}

.comment-table {
  width: 100%;
  min-width: 760px;
  table-layout: fixed;
  border-collapse: collapse;
  text-align: left;
}

.comment-table th,
.comment-table td {
  padding: 12px;
  border: 1px solid #ddd;
  vertical-align: top;
  overflow-wrap: anywhere;
}

.comment-table th {
  background-color: #f8f9fa;
  color: #2c3e50;
}

.comment-table th:nth-child(1) {
  width: 12%;
}

.comment-table th:nth-child(2) {
  width: 17%;
}

.comment-table th:nth-child(3) {
  width: 35%;
}

.comment-table th:nth-child(4),
.comment-table th:nth-child(5) {
  width: 12%;
}

.comment-table th:nth-child(6) {
  width: 12%;
}

.comment-content {
  line-height: 1.5;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 8px;
}

.author-avatar-link {
  display: block;
  flex: 0 0 36px;
}

.author-avatar {
  display: block;
  width: 36px;
  height: 36px;
  object-fit: cover;
  border-radius: 50%;
}

.comment-thumbnail {
  display: block;
  width: 96px;
  height: 72px;
  object-fit: cover;
  border-radius: 4px;
}

.file-download {
  display: inline-block;
  padding: 6px 10px;
  color: #fff;
  background-color: #007bff;
  border-radius: 4px;
  text-decoration: none;
  white-space: nowrap;
}

.file-download:hover {
  background-color: #0056b3;
}

.empty-value,
.empty-list {
  color: #777;
}

.empty-list {
  text-align: center;
}

.comment-actions {
  white-space: normal;
}

.comment-actions button {
  margin: 0 4px 4px 0;
  padding: 6px 8px;
  color: #fff;
  background-color: #42b983;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}

.comment-actions button:hover {
  background-color: #369870;
}

.comment-actions .new-replies-btn {
  background-color: #007bff;
}

.comment-actions .new-replies-btn:hover {
  background-color: #0056b3;
}

.reply-form {
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.replies-cell {
  padding: 16px !important;
  background-color: #fcfcfc;
}

.empty-replies {
  margin: 0;
}
</style>
