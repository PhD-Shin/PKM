import { App, TFile, moment } from "obsidian";

export interface Template {
  id: string;
  name: string;
  description: string;
  icon: string;
  fileName: string;
  suggestedFolder?: string;
}

export const TEMPLATES: Template[] = [
  {
    id: "meeting",
    name: "Meeting Note",
    description: "회의록 작성 - Agenda, Decisions, Action Items 자동 구조화",
    icon: "📅",
    fileName: "meeting-note.md",
    suggestedFolder: "Meetings",
  },
  {
    id: "idea",
    name: "Idea Note",
    description: "아이디어 메모 - Core Concept와 Applications 정리",
    icon: "💡",
    fileName: "idea-note.md",
    suggestedFolder: "Ideas",
  },
  {
    id: "project",
    name: "Project Note",
    description: "프로젝트 계획 - Goal, Tasks, Resources 관리",
    icon: "📁",
    fileName: "project-note.md",
    suggestedFolder: "Projects",
  },
  {
    id: "weekly-review",
    name: "Weekly Review",
    description: "주간 리뷰 - 완료 항목, 인사이트, 다음 주 계획",
    icon: "📝",
    fileName: "weekly-review.md",
    suggestedFolder: "Reviews",
  },
];

export class TemplateService {
  constructor(private app: App) {}

  /**
   * 템플릿 파일 읽기
   */
  async getTemplateContent(template: Template): Promise<string> {
    const templatePath = `templates/${template.fileName}`;
    const file = this.app.vault.getAbstractFileByPath(templatePath);

    if (!file || !(file instanceof TFile)) {
      throw new Error(`Template not found: ${templatePath}`);
    }

    let content = await this.app.vault.read(file);

    // 템플릿 변수 치환
    content = this.processTemplateVariables(content);

    return content;
  }

  /**
   * 템플릿 변수 처리 ({{variable}} 형식)
   */
  private processTemplateVariables(content: string): string {
    const now = moment();

    return content
      .replace(/\{\{date:YYYY-MM-DD\}\}/g, now.format("YYYY-MM-DD"))
      .replace(/\{\{date:YYYY-MM-DD HH:mm\}\}/g, now.format("YYYY-MM-DD HH:mm"))
      .replace(/\{\{date:YYYY-\[W\]WW\}\}/g, now.format("YYYY-[W]WW"))
      .replace(/\{\{title\}\}/g, "")
      .replace(/\{\{title:lower\}\}/g, "");
  }

  /**
   * 템플릿으로부터 새 노트 생성
   */
  async createNoteFromTemplate(
    template: Template,
    customTitle?: string
  ): Promise<TFile> {
    const content = await this.getTemplateContent(template);

    // 파일명 생성
    const title = customTitle || this.generateDefaultTitle(template);
    const folder = template.suggestedFolder || "";
    const fileName = `${folder ? folder + "/" : ""}${title}.md`;

    // 폴더 생성 (존재하지 않으면)
    if (folder) {
      await this.ensureFolderExists(folder);
    }

    // 파일 생성
    const processedContent = content
      .replace(/\{\{title\}\}/g, title)
      .replace(/\{\{title:lower\}\}/g, title.toLowerCase().replace(/\s+/g, "-"));

    const file = await this.app.vault.create(fileName, processedContent);

    return file;
  }

  /**
   * 기본 제목 생성
   */
  private generateDefaultTitle(template: Template): string {
    const now = moment();

    switch (template.id) {
      case "meeting":
        return `Meeting ${now.format("YYYY-MM-DD")}`;
      case "idea":
        return `Idea ${now.format("YYYY-MM-DD")}`;
      case "project":
        return `Project ${now.format("YYYY-MM-DD")}`;
      case "weekly-review":
        return `Weekly Review ${now.format("YYYY-[W]WW")}`;
      default:
        return `Note ${now.format("YYYY-MM-DD")}`;
    }
  }

  /**
   * 폴더 생성 (재귀적)
   */
  private async ensureFolderExists(folderPath: string): Promise<void> {
    const folder = this.app.vault.getAbstractFileByPath(folderPath);
    if (!folder) {
      await this.app.vault.createFolder(folderPath);
    }
  }

  /**
   * 모든 템플릿 목록 가져오기
   */
  getTemplates(): Template[] {
    return TEMPLATES;
  }

  /**
   * 특정 템플릿 가져오기
   */
  getTemplate(id: string): Template | undefined {
    return TEMPLATES.find((t) => t.id === id);
  }
}
