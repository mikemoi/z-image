import { CLASSIFICATION_SECTIONS } from '../classification'

export default function ClassificationGuide() {
  return (
    <details className="class-guide">
      <summary>分类说明</summary>
      <div className="class-guide-body">
        {CLASSIFICATION_SECTIONS.map((section) => (
          <section key={section.title}>
            <h3>{section.title}</h3>
            {section.items.map(([name, meaning]) => <p key={name}><b>{name}</b>：{meaning}</p>)}
          </section>
        ))}
        <section>
          <h3>相关主题 = 这条内容还涉及什么</h3>
          <p>最多 2 个，只从固定主题中选择，用来处理重叠内容。</p>
        </section>
        <section>
          <h3>标签 = 更细的关键词</h3>
          <p>最多 5 个，例如专注达、反跳、他人经验、NIE、1Panel、Binance、阅读、风控。</p>
          <p>“他人经验”是标签，不是来源。</p>
        </section>
        <section>
          <h3>来源 = 从哪里进入系统</h3>
          <p><b>自己</b>：用户自己写的</p>
          <p><b>截图</b>：截图或 OCR 来的</p>
          <p><b>文件</b>：PDF、DOCX、合同等文件来的</p>
          <p>来源只表示进入方式，不表示可信度。</p>
        </section>
      </div>
    </details>
  )
}
