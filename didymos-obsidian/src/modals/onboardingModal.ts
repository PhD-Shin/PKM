import { App, Modal } from "obsidian";
import { TemplateService } from "../services/templateService";

export class OnboardingModal extends Modal {
  private templateService: TemplateService;
  private onComplete: () => void;

  constructor(app: App, templateService: TemplateService, onComplete: () => void) {
    super(app);
    this.templateService = templateService;
    this.onComplete = onComplete;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("didymos-onboarding-modal");

    // Header
    const header = contentEl.createDiv("didymos-onboarding-header");
    header.createEl("h1", { text: "🎉 Welcome to Didymos!" });
    header.createEl("p", {
      text: 'Didymos는 "Zettelkasten을 자동으로 해주는 두 번째 두뇌"입니다.',
      cls: "didymos-onboarding-subtitle",
    });

    // Description
    const desc = contentEl.createDiv("didymos-onboarding-description");
    desc.createEl("p", {
      text: "Didymos는 노트 작성 시 자동으로:",
    });

    const features = desc.createEl("ul");
    features.createEl("li", { text: "📌 Topics, Projects, Tasks, People 추출" });
    features.createEl("li", { text: "🔗 관련 노트 자동 추천" });
    features.createEl("li", { text: "📊 지식 그래프 시각화" });
    features.createEl("li", { text: "💡 인사이트 및 패턴 발견" });

    // Quick Start Section
    const quickStart = contentEl.createDiv("didymos-onboarding-quickstart");
    quickStart.createEl("h2", { text: "💡 빠른 시작 방법" });
    quickStart.createEl("p", {
      text: "추천 템플릿으로 시작하면 Didymos가 더 정확하게 노트를 분석할 수 있습니다:",
    });

    // Template Grid
    const templateGrid = quickStart.createDiv("didymos-template-grid");

    const templates = this.templateService.getTemplates();
    templates.forEach((template) => {
      const card = templateGrid.createDiv("didymos-template-card");
      card.createEl("div", { text: template.icon, cls: "template-icon" });
      card.createEl("h3", { text: template.name });
      card.createEl("p", { text: template.description });

      const btn = card.createEl("button", { text: "사용하기" });
      btn.addEventListener("click", async () => {
        await this.createFromTemplate(template.id);
      });
    });

    // Actions
    const actions = contentEl.createDiv("didymos-onboarding-actions");

    const exploreBtn = actions.createEl("button", {
      text: "템플릿 갤러리 둘러보기",
      cls: "mod-cta",
    });
    exploreBtn.addEventListener("click", () => {
      this.close();
      this.openTemplateGallery();
    });

    const skipBtn = actions.createEl("button", {
      text: "직접 작성하기",
    });
    skipBtn.addEventListener("click", () => {
      this.completeOnboarding();
    });

    // Footer
    const footer = contentEl.createDiv("didymos-onboarding-footer");
    footer.createEl("p", {
      text: "💡 Tip: 템플릿은 나중에도 Command Palette (Ctrl/Cmd + P)에서 사용할 수 있습니다.",
      cls: "didymos-tip",
    });
  }

  private async createFromTemplate(templateId: string) {
    const template = this.templateService.getTemplate(templateId);
    if (!template) return;

    try {
      const file = await this.templateService.createNoteFromTemplate(template);

      // 생성된 노트 열기
      const leaf = this.app.workspace.getLeaf(false);
      await leaf.openFile(file);

      // 온보딩 완료
      this.completeOnboarding();
    } catch (error) {
      console.error("Failed to create note from template:", error);
      // 에러 처리
    }
  }

  private openTemplateGallery() {
    // 템플릿 갤러리 모달 열기 (다음 구현)
    import("./templateGalleryModal").then(({ TemplateGalleryModal }) => {
      new TemplateGalleryModal(this.app, this.templateService, () => {
        this.completeOnboarding();
      }).open();
    });
  }

  private completeOnboarding() {
    this.close();
    this.onComplete();
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
