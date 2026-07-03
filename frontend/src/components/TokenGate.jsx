import { useState } from 'react'
import { getToken, setToken } from '../api'

// 单用户:首次进来输入一次 token 存本地。默认预填开发 token,方便本机测试。
export default function TokenGate({ children }) {
  const [token, setTok] = useState(getToken())
  const [input, setInput] = useState(getToken() || 'dev-token-change-me')

  if (token) return children

  return (
    <div className="gate">
      <h1>zbrain</h1>
      <p>输入访问口令</p>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="token"
        autoCapitalize="off"
        autoCorrect="off"
      />
      <button
        className="btn-primary"
        onClick={() => {
          setToken(input.trim())
          setTok(input.trim())
        }}
      >
        进入
      </button>
    </div>
  )
}
