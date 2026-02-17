import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ProjectCard } from "./ProjectCard";
import type { Project } from "@/api/types";

const mockProject: Project = {
  id: 1,
  name: "Test Novel",
  description: "A test description",
  source_language: "ko",
  target_language: "en",
  genre: "Fantasy",
  pipeline_type: "cot",
  llm_provider: "gemini",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-02T00:00:00Z",
  chapter_count: 3,
};

describe("ProjectCard", () => {
  it("renders project name and language pair", () => {
    render(
      <ProjectCard project={mockProject} onClick={vi.fn()} onDelete={vi.fn()} />
    );

    expect(screen.getByText("Test Novel")).toBeInTheDocument();
    expect(screen.getByText("Korean")).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();
  });

  it("renders description when present", () => {
    render(
      <ProjectCard project={mockProject} onClick={vi.fn()} onDelete={vi.fn()} />
    );

    expect(screen.getByText("A test description")).toBeInTheDocument();
  });

  it("renders chapter count", () => {
    render(
      <ProjectCard project={mockProject} onClick={vi.fn()} onDelete={vi.fn()} />
    );

    expect(screen.getByText("3 chapters")).toBeInTheDocument();
  });

  it("renders singular chapter label for 1 chapter", () => {
    render(
      <ProjectCard
        project={{ ...mockProject, chapter_count: 1 }}
        onClick={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.getByText("1 chapter")).toBeInTheDocument();
  });

  it("calls onClick when card is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <ProjectCard project={mockProject} onClick={onClick} onDelete={vi.fn()} />
    );

    await user.click(screen.getByText("Test Novel"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("calls onDelete when delete button is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const onDelete = vi.fn();

    render(
      <ProjectCard project={mockProject} onClick={onClick} onDelete={onDelete} />
    );

    const deleteButton = screen.getByTitle("Delete project");
    await user.click(deleteButton);

    expect(onDelete).toHaveBeenCalledTimes(1);
    // Should NOT trigger card navigation
    expect(onClick).not.toHaveBeenCalled();
  });

  it("does not render description when null", () => {
    render(
      <ProjectCard
        project={{ ...mockProject, description: null }}
        onClick={vi.fn()}
        onDelete={vi.fn()}
      />
    );

    expect(screen.queryByText("A test description")).not.toBeInTheDocument();
  });
});
