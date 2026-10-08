"use client";

import Container from "@cloudscape-design/components/container";
import Header from "@cloudscape-design/components/header";
import TagEditor from "@cloudscape-design/components/tag-editor";
import type { TagEditorProps } from "@cloudscape-design/components/tag-editor";

import { InfoLink } from "@/components/shell/help-context";
import type { Tag } from "@/lib/api/types";

export type EditableTag = TagEditorProps.Tag;

const TAG_LIMIT = 50;

/** Tags as the API expects them: rows marked for removal and blank rows are dropped. */
export function toApiTags(tags: readonly EditableTag[]): Tag[] {
  return tags
    .filter((tag) => !tag.markedForRemoval && tag.key.trim())
    .map((tag) => ({ key: tag.key.trim(), value: tag.value }));
}

export function toEditableTags(tags: readonly Tag[]): EditableTag[] {
  return tags.map((tag) => ({ key: tag.key, value: tag.value ?? "", existing: true }));
}

interface TagsContainerProps {
  tags: readonly EditableTag[];
  onChange: (tags: readonly EditableTag[]) => void;
}

/** The "Tags" section of the create and edit hosted zone pages. */
export function TagsContainer({ tags, onChange }: TagsContainerProps) {
  return (
    <Container
      header={
        <Header
          variant="h2"
          info={<InfoLink topic="tags" />}
          description="Apply tags to hosted zones to help organize and identify them."
        >
          Tags
        </Header>
      }
    >
      <TagEditor
        tags={tags}
        tagLimit={TAG_LIMIT}
        onChange={({ detail }) => onChange(detail.tags)}
        i18nStrings={{
          keyHeader: "Key",
          valueHeader: "Value - optional",
          keyPlaceholder: "Enter key",
          valuePlaceholder: "Enter value",
          addButton: "Add tag",
          removeButton: "Remove tag",
          emptyTags: "No tags associated with the resource.",
          tagLimit: (available) => `You can add up to ${available} more tags.`,
        }}
      />
    </Container>
  );
}
