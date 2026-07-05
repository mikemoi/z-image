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
          <h3>标签 = 具体讲什么</h3>
          <p>例如 ADHD、药物、专注达、他人经验、合同、西班牙语、交易、正向循环。</p>
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
