import { App, Modal, TFile } from "obsidian";
import { TemplateService, Template } from "../services/templateService";

export class TemplateGalleryModal extends Modal {
  private templateService: TemplateService;
  private onComplete: () => void;
  private selectedTemplate: Template | null = null;

  constructor(
    app: App,
    templateService: TemplateService,
    onComplete: () => void
  ) {
    super(app);
    this.templateService = templateService;
    this.onComplete = onComplete;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("didymos-template-gallery");

    // Header
    const header = contentEl.createDiv("template-gallery-header");
    header.createEl("h1", { text: "📚 Template Gallery" });
    header.createEl("p", {
      text: "Didymos 추천 노트 템플릿으로 바로 시작하세요",
    });

    // Template Grid
    const grid = contentEl.createDiv("template-gallery-grid");

    const templates = this.templateService.getTemplates();
    templates.forEach((template) => {
      this.renderTemplateCard(grid, template);
    });

    // Footer
    const footer = contentEl.createDiv("template-gallery-footer");
    const closeBtn = footer.createEl("button", { text: "닫기" });
    closeBtn.addEventListener("click", () => {
      this.close();
      this.onComplete();
    });
  }

  private renderTemplateCard(container: HTMLElement, template: Template) {
    const card = container.createDiv("template-card");

    // Icon
    card.createEl("div", { text: template.icon, cls: "template-card-icon" });

    // Content
    const content = card.createDiv("template-card-content");
    content.createEl("h3", { text: template.name });
    content.createEl("p", { text: template.description });

    if (template.suggestedFolder) {
      content.createEl("span", {
        text: `📁 ${template.suggestedFolder}/`,
        cls: "template-card-folder",
      });
    }

    // Actions
    const actions = card.createDiv("template-card-actions");

    const previewBtn = actions.createEl("button", { text: "미리보기" });
    previewBtn.addEventListener("click", () => {
      this.showPreview(template);
    });

    const useBtn = actions.createEl("button", {
      text: "사용하기",
      cls: "mod-cta",
    });
    useBtn.addEventListener("click", async () => {
      await this.createFromTemplate(template);
    });
  }

  private async showPreview(template: Template) {
    try {
      const content = await this.templateService.getTemplateContent(template);

      // 프리뷰 모달
      const previewModal = new Modal(this.app);
      previewModal.titleEl.setText(`${template.icon} ${template.name} - 미리보기`);

      const { contentEl } = previewModal;
      contentEl.addClass("template-preview-modal");

      const codeBlock = contentEl.createEl("pre");
      const code = codeBlock.createEl("code");
      code.setText(content);

      const actions = contentEl.createDiv("template-preview-actions");

      const closeBtn = actions.createEl("button", { text: "닫기" });
      closeBtn.addEventListener("click", () => previewModal.close());

      const useBtn = actions.createEl("button", {
        text: "이 템플릿 사용",
        cls: "mod-cta",
      });
      useBtn.addEventListener("click", async () => {
        previewModal.close();
        await this.createFromTemplate(template);
      });

      previewModal.open();
    } catch (error) {
      console.error("Failed to load template preview:", error);
    }
  }

  private async createFromTemplate(template: Template) {
    // 제목 입력 받기
    const title = await this.promptForTitle(template);
    if (!title) return; // 취소

    try {
      const file = await this.templateService.createNoteFromTemplate(
        template,
        title
      );

      // 생성된 노트 열기
      const leaf = this.app.workspace.getLeaf(false);
      await leaf.openFile(file);

      this.close();
      this.onComplete();
    } catch (error) {
      console.error("Failed to create note from template:", error);
      // 에러 메시지 표시
    }
  }

  private promptForTitle(template: Template): Promise<string | null> {
    return new Promise((resolve) => {
      const modal = new Modal(this.app);
      modal.titleEl.setText(`${template.icon} ${template.name} - 제목 입력`);

      const { contentEl } = modal;
      contentEl.createEl("p", { text: "노트 제목을 입력하세요:" });

      const input = contentEl.createEl("input", {
        type: "text",
        placeholder: "예: Project Kickoff Meeting",
      });
      input.style.width = "100%";
      input.style.marginBottom = "10px";

      const actions = contentEl.createDiv();
      actions.style.display = "flex";
      actions.style.gap = "10px";
      actions.style.justifyContent = "flex-end";

      const cancelBtn = actions.createEl("button", { text: "취소" });
      cancelBtn.addEventListener("click", () => {
        modal.close();
        resolve(null);
      });

      const createBtn = actions.createEl("button", {
        text: "생성",
        cls: "mod-cta",
      });
      createBtn.addEventListener("click", () => {
        const title = input.value.trim();
        if (title) {
          modal.close();
          resolve(title);
        }
      });

      // Enter key handling
      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          const title = input.value.trim();
          if (title) {
            modal.close();
            resolve(title);
          }
        } else if (e.key === "Escape") {
          modal.close();
          resolve(null);
        }
      });

      modal.open();
      input.focus();
    });
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
