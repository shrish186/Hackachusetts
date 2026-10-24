import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type {
  Conditions,
  MetaResponse,
  RiskCell,
  Sighting,
  Zone,
} from '@/api/types';

/** Load source metadata once on mount. */
export function useMeta(): MetaResponse | null {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  useEffect(() => {
    let alive = true;
    api.getMeta().then((m) => alive && setMeta(m));
    return () => {
      alive = false;
    };
  }, []);
  return meta;
}

/** Load zones once (they carry their own active windows). */
export function useZones(timeIso: string): Zone[] {
  const [zones, setZones] = useState<Zone[]>([]);
  useEffect(() => {
    let alive = true;
    api.getZones(timeIso).then((z) => alive && setZones(z));
    return () => {
      alive = false;
    };
  }, [timeIso]);
  return zones;
}

export function useSightings(): Sighting[] {
  const [sightings, setSightings] = useState<Sighting[]>([]);
  useEffect(() => {
    let alive = true;
    api.getSightings().then((s) => alive && setSightings(s));
    return () => {
      alive = false;
    };
  }, []);
  return sightings;
}

export function useConditions(timeIso: string, enabled: boolean): Conditions[] {
  const [data, setData] = useState<Conditions[]>([]);
  useEffect(() => {
    if (!enabled) {
      setData([]);
      return;
    }
    let alive = true;
    api.getConditions(timeIso).then((d) => alive && setData(d));
    return () => {
      alive = false;
    };
  }, [timeIso, enabled]);
  return data;
}

export function useRisk(
  timeIso: string,
  speedKn: number,
  enabled: boolean,
): RiskCell[] {
  const [data, setData] = useState<RiskCell[]>([]);
  useEffect(() => {
    if (!enabled) {
      setData([]);
      return;
    }
    let alive = true;
    api.getRisk(timeIso, speedKn).then((d) => alive && setData(d));
    return () => {
      alive = false;
    };
  }, [timeIso, speedKn, enabled]);
  return data;
}
