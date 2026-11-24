import { StyleLanding, generateStyleMetadata } from "../components/style-landing";

export async function generateMetadata({ searchParams }: { searchParams: Promise<{ arma?: string | string[] }> }) {
  return generateStyleMetadata("daytona", searchParams);
}

export default function Page() {
  return <StyleLanding cls="daytona" />;
}
