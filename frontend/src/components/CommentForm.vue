<template>
  <div class="comment-form">
    <div v-if="formError" class="error">
      {{ formError }}
    </div>
    <form class="comment-form-layout" @submit.prevent="onSubmit">
      <label class="visually-hidden" :for="contentInputId">Comment text</label>
      <textarea :id="contentInputId" v-model="content" placeholder="Write a comment..." required autocomplete="off" rows="3"></textarea>
      <div class="comment-form-controls">
        <label class="attachment-button">
          Add text file
          <input type="file" accept=".txt" @change="onFileChange" />
        </label>
        <label class="attachment-button">
          Add image
          <input type="file" accept="image/*" @change="onImageChange" />
        </label>
        <button type="submit" class="submit-button" :disabled="submitting">
          {{ submitting ? 'Submitting...' : 'Submit' }}
        </button>
      </div>
    </form>
    <div class="selected-files" aria-live="polite">
      <span v-if="fileFile">{{ fileFile.name }}</span>
      <span v-if="imageFile">{{ imageFile.name }}</span>
    </div>
  </div>
</template>

<script>
let nextFormId = 0

export default {
  name: 'CommentForm',
  props: {
    parentId: {
      type: [Number, String],
      default: null,
      validator: value => {
        // Allow null, numbers, or numeric strings
        return value === null ||
               typeof value === 'number' ||
               (typeof value === 'string' && !isNaN(Number(value)))
      }
    }
  },
  data() {
    return {
      formId: ++nextFormId,
      content: '',
      imageFile: null,
      fileFile: null,
      submitting: false,
      formError: ''
    }
  },
  watch: {
    content() {
      // Clear form error when user starts typing
      if (this.formError) {
        this.formError = ''
      }
    }
  },
  computed: {
    contentInputId() {
      return `comment-content-${this.formId}`
    }
  },
  methods: {
    onImageChange(event) {
      this.imageFile = event.target.files[0] || null
    },
    onFileChange(event) {
      this.fileFile = event.target.files[0] || null
    },
    onSubmit() {
      // Clear any previous form error
      this.formError = ''

      if (!this.content.trim()) {
        this.formError = 'Please enter a comment before submitting.'
        return
      }

      this.submitting = true

      const formData = new FormData()
      formData.append('content', this.content)
      if (this.parentId !== null) {
        formData.append('parent', this.parentId)
      }
      if (this.imageFile) {
        formData.append('image', this.imageFile)
      }
      if (this.fileFile) {
        formData.append('file', this.fileFile)
      }

      this.$emit('commentCreated', formData)

      // Reset submitting state after a brief delay to allow UI update
      setTimeout(() => {
        this.submitting = false
      }, 100)
    },
    clearForm() {
      this.content = ''
      this.imageFile = null
      this.fileFile = null
      const form = this.$el.querySelector('form')
      if (form) form.reset()
    }
  }
}
</script>

<style scoped>
.comment-form {
  margin: 0 0 16px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #f8f9fa;
}

.comment-form-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px;
  gap: 10px;
  align-items: stretch;
}

.comment-form textarea {
  width: 100%;
  min-height: 84px;
  padding: 10px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
}

.comment-form-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attachment-button,
.submit-button {
  display: flex;
  min-height: 30px;
  align-items: center;
  justify-content: center;
  padding: 5px 8px;
  box-sizing: border-box;
  border: 0;
  border-radius: 4px;
  color: #fff;
  background: #42b983;
  cursor: pointer;
  font: inherit;
  font-size: 0.9rem;
  min-width: 0;
}

.attachment-button:hover,
.submit-button:hover {
  background: #369870;
}
.attachment-button:focus-visible,
.submit-button:focus-visible {
  outline: 2px solid #2c3e50;
  outline-offset: 2px;
}

.attachment-button input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
  clip-path: inset(50%);
}

.attachment-button:focus-within {
  outline: 2px solid #2c3e50;
  outline-offset: 2px;
}

.selected-files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  color: #555;
  font-size: 0.85rem;
}
.error {
  color: #dc3545;
  font-size: 0.875rem;
  margin-top: 6px;
  margin-bottom: 12px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 520px) {
  .comment-form-layout {
    grid-template-columns: minmax(0, 1fr) 140px;
  }

  .attachment-button,
  .submit-button {
    padding: 5px;
    font-size: 0.8rem;
    min-height: 44px;
    min-width: 44px;
  }
}
</style>