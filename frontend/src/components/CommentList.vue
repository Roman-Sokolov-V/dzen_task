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
                <div class="author-details">
                  <span class="author-name">{{ comment.author }}</span>
                  <span v-if="comment.email" class="author-email">{{ comment.email }}</span>
                </div>
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
              <span v-else class="empty-value">No image attached</span>
            </td>
            <td>
              <a
                v-if="comment.file"
                :href="getDownloadUrl(comment.file)"
                :download="getFileName(comment.file)"
                class="file-download"
              >
                Download file
              </a>
              <span v-else class="empty-value">No file attached</span>
            </td>
            <td class="comment-actions">
              <button type="button" @click="toggleReplyForm(comment.id)" @keydown.enter="toggleReplyForm(comment.id)" @keydown.space="toggleReplyForm(comment.id)">Reply</button>
              <button type="button" class="expand-btn" @click="toggleExpand(comment)"
                      :aria-label="expanded[comment.id] ? 'Collapse reply' : 'Expand reply'"
                      :aria-expanded="expanded[comment.id]">
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
                <CommentForm :parentId="comment.id" @commentCreated="handleCommentCreated" ref="replyForm" />
              </div>
            </td>
          </tr>
          <tr v-if="expanded[comment.id]">
            <td colspan="6" class="replies-cell">
              <!-- TODO: Consider implementing virtualization for large comment trees to improve performance -->
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
                No replies yet. Be the first to reply!
              </p>
            </td>
          </tr>
        </template>
        <tr v-if="comments.length === 0">
          <td colspan="6" class="empty-list">No comments yet. Be the first to comment!</td>
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
      loadingReplies: {},
      replyTreeCache: new Map() // Stores { commentId: { data: *, timestamp: * } }
    }
  },
  watch: {
    comments() {
      // Reset expanded state when comments list changes to prevent showing stale replies
      this.expanded = {}
    },
    lastCreatedReply(reply) {
      // Safely check if the new reply is for the currently open reply form
      if (reply &&
          typeof reply === 'object' &&
          reply !== null &&
          'parentId' in reply &&
          reply.parentId !== null &&
          Number(this.showReplyForm) === reply.parentId) {
        this.showReplyForm = null
      }
    },
    showReplyForm(val) {
      // Clear the reply form and reset submitting state when it's hidden (after successful submission or cancellation)
      if (val === null && this.$refs.replyForm) {
        this.$refs.replyForm.clearForm()
        // Reset submitting state in case form was hidden during submission
        if (this.$refs.replyForm.submitting !== undefined) {
          this.$refs.replyForm.submitting = false
        }
      }
    }
  },
  methods: {
    toggleReplyForm(commentId) {
      // Validate commentId is a valid number
      if (commentId === null || commentId === undefined || isNaN(Number(commentId))) {
        console.error('Invalid commentId provided to toggleReplyForm:', commentId)
        return
      }
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
      // Show loading state while fetching replies if needed
      if (!this.hasLoadedChildren(commentId) || this.newReplyCounts[commentId]) {
        this.refreshReplies(commentId)
        // Note: expanded will be set to true in refreshReplies after data loads
      } else {
        this.expanded[commentId] = true
      }
    },
    refreshReplies(commentId) {
      if (this.loadingReplies[commentId]) return

      // Check cache first - if we have fresh data, use it
      const cached = this.replyTreeCache.get(commentId)
      if (cached) {
        const age = Date.now() - cached.timestamp
        // Use cache if less than 5 minutes old
        if (age < 5 * 60 * 1000) {
          this.setLoadedChildren(commentId, cached.data)
          this.expanded[commentId] = true
          this.clearReplyNotifications(commentId, cached.data)
          return
        }
      }

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

          // Cache the result
          this.replyTreeCache.set(commentId, {
            data: childrenData,
            timestamp: Date.now()
          })
        })
        .catch(error => {
          console.error('Error fetching comment tree:', error)
        })
        .finally(() => {
          this.loadingReplies[commentId] = false
        })
    },
    convertApiTreeToInternalFormat(apiComment, depth = 0) {
      // Null safety
      if (!apiComment || typeof apiComment !== 'object') return null

      // Prevent excessive recursion depth (protect against circular references)
      if (depth > 10) {
        console.warn('Maximum depth exceeded in comment tree conversion')
        return null
      }

      try {
        const { replies, ...commentWithoutReplies } = apiComment
        const commentWithChildren = { ...commentWithoutReplies, children: [] }
        if (Array.isArray(replies)) {
          commentWithChildren.children = replies.map(reply =>
            this.convertApiTreeToInternalFormat(reply, depth + 1)
          ).filter(child => child !== null) // Filter out any null results
        }
        return commentWithChildren
      } catch (error) {
        console.error('Error converting comment tree node:', error, apiComment)
        return null
      }
    },
    getPublicMediaUrl(mediaUrl) {
      try {
        const url = new URL(mediaUrl, window.location.origin)
        const s3Path = '/storage/v1/s3/'
        if (url.pathname.includes(s3Path)) {
          url.pathname = url.pathname.replace(s3Path, '/storage/v1/object/public/')
          url.hostname = url.hostname.replace('.storage.supabase.co', '.supabase.co')
        }
        return url.toString()
      } catch (error) {
        console.error('Error parsing media URL:', error, mediaUrl)
        // Return a fallback URL or the original if we can't process it
        return mediaUrl
      }
    },
    getFileName(fileUrl) {
      try {
        const path = new URL(fileUrl, window.location.origin).pathname
        // Extract filename and sanitize it
        let filename = decodeURIComponent(path.substring(path.lastIndexOf('/') + 1)) || 'comment-file'
        // Remove any potential path traversal attempts
        filename = filename.replace(/[\\/:*?"<>|]/g, '')
        // Limit length to prevent extremely long filenames
        if (filename.length > 255) {
          filename = filename.substring(0, 255)
        }
        return filename || 'comment-file'
      } catch (error) {
        console.error('Error parsing file URL:', error, fileUrl)
        return 'unknown-file'
      }
    },
    getDownloadUrl(mediaUrl) {
      try {
        const url = new URL(this.getPublicMediaUrl(mediaUrl))
        const filename = this.getFileName(mediaUrl)
        // Additional security validation for download attribute
        // Ensure filename doesn't contain dangerous characters
        const safeFilename = filename.replace(/[\\/:%*?"<>|]/g, '_')
        // Limit length
        const limitedFilename = safeFilename.length > 200 ?
          safeFilename.substring(0, 200) : safeFilename
        url.searchParams.set('download', limitedFilename)
        return url.toString()
      } catch (error) {
        console.error('Error creating download URL:', error, mediaUrl)
        // Fallback to a safe URL
        const fallbackUrl = new URL('/', window.location.origin)
        fallbackUrl.searchParams.set('error', 'invalid_media_url')
        return fallbackUrl.toString()
      }
    },
    handleCommentCreated(comment) {
      // Validate comment object structure
      if (!comment || typeof comment !== 'object') {
        console.error('Invalid comment object received:', comment)
        return
      }

      // Basic validation - ensure it has an id if it's a meaningful comment
      if ('id' in comment && comment.id === null) {
        console.warn('Comment with null id received:', comment)
      }

      // Emit the validated comment
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
.comment-table td:nth-child(2) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.comment-table th {
  background-color: #f8f9fa;
  color: #2c3e50;
}

.comment-table th:nth-child(1) {
  width: 15%;
}

.comment-table th:nth-child(2) {
  width: 17%;
}

.comment-table th:nth-child(3) {
  width: 32%;
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
  overflow-wrap: break-word;
  hyphens: auto;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 8px;
}
.author-details {
  display: flex;
  flex-direction: column;
}
.author-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
  font-weight: 600;
}
.author-email {
  font-size: 0.875em;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}

.author-avatar-link {
  display: block;
  flex: 0 0 36px;
}

.comment-thumbnail {
  display: block;
  width: 96px;
  height: 72px;
  object-fit: cover;
  border-radius: 4px;
}
/* Disable animations on images when user prefers reduced motion */
@media (prefers-reduced-motion: reduce) {
  .author-avatar,
  .comment-thumbnail {
    animation: none !important;
    transition: none !important;
  }
}
.author-avatar,
.comment-thumbnail {
  /* Respect user's preference for reduced motion */
  @media (prefers-reduced-motion: reduce) {
    animation-duration: 0.001s !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001s !important;
  }
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
.empty-replies {
  text-align: center;
  padding: 20px;
  font-size: 1rem;
  color: #555;
  font-style: italic;
}

.empty-list {
  text-align: center;
  padding: 30px;
  font-size: 1.1rem;
  color: #555;
}

.comment-actions {
  white-space: normal;
  touch-action: manipulation;
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
.comment-actions .new-replies-btn:focus-visible {
  outline: 2px solid #2c3e50;
  outline-offset: 2px;
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
