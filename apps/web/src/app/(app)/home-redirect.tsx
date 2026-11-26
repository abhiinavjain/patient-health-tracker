"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMe } from "@/lib/hooks";
import { LoadingRows } from "@/components/states";

const HOME = { clinician: "/dashboard", patient: "/me", admin: "/admin" } as const;

export function HomeRedirect() {
  const { data: me } = useMe();
  const router = useRouter();
  useEffect(() => {
    if (me) router.replace(HOME[me.role]);
  }, [me, router]);
  return <LoadingRows rows={3} />;
}
