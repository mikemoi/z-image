import { useEffect, useState } from 'react'
import { fileObjectUrl } from '../api'

// 原图接口需鉴权,<img src> 不带 header,所以 fetch blob → objectURL。
// thumb=true 时走列表缩略图(长边 960px,省流量);详情页/放大保持默认原图。
export default function Img({ checksum, alt = '', className, onClick, thumb = false }) {
  const [url, setUrl] = useState(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    let revoked = null
    let alive = true
    setUrl(null)
    setErr(false)
    fileObjectUrl(checksum, { thumb })
      .then((u) => {
        if (alive) { setUrl(u); revoked = u }
        else URL.revokeObjectURL(u)
      })
      .catch(() => alive && setErr(true))
    return () => {
      alive = false
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [checksum, thumb])

  if (err) return <div className={`img-fallback ${className || ''}`}>图片丢失</div>
  if (!url) return <div className={`img-skeleton ${className || ''}`} />
  return <img src={url} alt={alt} className={className} onClick={onClick} loading="lazy" />
}
