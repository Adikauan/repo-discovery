import type { PropsWithChildren } from 'react'; import { ContentCard } from '../layout/ContentCard'; import { SectionHeader } from '../layout/SectionHeader';
export function DashboardSection({title,children}:PropsWithChildren<{title:string}>){return <ContentCard><SectionHeader title={title}/>{children}</ContentCard>}
