/**
 * Compress image if it exceeds maxSizeKB using Canvas API
 * @param {File|Blob} file - The image file to compress
 * @param {number} maxSizeKB - Maximum size in KB (default 18MB = 18432KB to leave margin for base64 overhead)
 * @returns {Promise<Blob|null>} - Compressed Blob or null if still too large
 */
export function compressImageIfNeeded(file, maxSizeKB = 18432) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        let quality = 0.8
        let width = img.width
        let height = img.height

        // Scale down if very large (max 3000px on any side)
        const maxDimension = 3000
        if (width > maxDimension || height > maxDimension) {
          const ratio = Math.min(maxDimension / width, maxDimension / height)
          width = Math.round(width * ratio)
          height = Math.round(height * ratio)
        }

        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, width, height)

        const tryCompress = () => {
          canvas.toBlob(
            (blob) => {
              if (blob.size > maxSizeKB * 1024 && quality > 0.3) {
                quality -= 0.2
                tryCompress()
              } else if (blob.size > maxSizeKB * 1024 && (width > 800 || height > 800)) {
                // Reduce dimensions by 20%
                width = Math.round(width * 0.8)
                height = Math.round(height * 0.8)
                canvas.width = width
                canvas.height = height
                ctx.drawImage(img, 0, 0, width, height)
                quality = 0.8 // Reset quality after resize
                tryCompress()
              } else {
                // Return null if still too large, otherwise return compressed blob
                resolve(blob.size > maxSizeKB * 1024 ? null : blob)
              }
            },
            'image/jpeg',
            quality
          )
        }
        tryCompress()
      }
      img.onerror = () => resolve(null)
      img.src = e.target.result
    }
    reader.onerror = () => resolve(null)
    reader.readAsDataURL(file)
  })
}
