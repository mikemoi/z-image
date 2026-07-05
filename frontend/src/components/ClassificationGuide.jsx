import { CLASSIFICATION_SECTIONS } from '../classification'

export default function ClassificationGuide() {
  return (
    <details className="class-guide">
      <summary>分类说明</summary>
      <div className="class-guide-body">
        <section>
          <h3>内容坐标说明</h3>
          <p>类型：这条内容是什么形态</p>
          <p>领域：属于哪个人生大区</p>
          <p>主题：主要讲什么</p>
          <p>子题：主题下面的固定细分</p>
          <p>相关：还涉及什么，最多 2 个</p>
          <p>标签：细节关键词</p>
          <p>来源：内容从哪里来</p>
        </section>
        {CLASSIFICATION_SECTIONS.map((section) => (
          <section key={section.title}>
            <h3>{section.title}</h3>
            {section.items.map(([name, meaning]) => <p key={name}><b>{name}</b>：{meaning}</p>)}
          </section>
        ))}
        <section>
          <h3>关联 = 还牵涉什么</h3>
          <p>最多 2 个，只从固定主题中选择，用来处理重叠内容。</p>
        </section>
        <section>
          <h3>标签 = 细节关键词</h3>
          <p>最多 5 个，例如专注达、反跳、他人经验、NIE、1Panel、Binance、阅读、风控。</p>
          <p>正式标签优先，候选标签需要批准；“他人经验”是标签，不是来源。</p>
        </section>
        <section>
          <h3>来源 = 从哪里来</h3>
          <p><b>我</b>：用户自己写的</p>
          <p><b>图片</b>：图片、截图或 OCR 来的</p>
          <p><b>文件</b>：PDF、DOCX、合同等文件来的</p>
          <p>来源只表示进入方式，不表示可信度。</p>
        </section>
      </div>
    </details>
  )
}
