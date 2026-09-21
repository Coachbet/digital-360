import { api } from "@/shared/api/client";

export interface OrganizationProfile {
  id: string;
  name: string;
  slug: string;

  brand_primary: string;
  brand_ink: string;
  brand_accent: string;
  tagline: string | null;
  logo_storage_key: string | null;
  deck_template_key: string | null;

  legal_name: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  tax_number_1_label: string;
  tax_number_1: string | null;
  tax_number_2_label: string;
  tax_number_2: string | null;
  registration_number: string | null;
  payment_terms: string | null;
  payment_details: string | null;
}

export const organizationApi = {
  profile: () => api.get<OrganizationProfile>("/organization"),

  update: (payload: Partial<OrganizationProfile>) =>
    api.put<OrganizationProfile>("/organization", payload),

  uploadLogo: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.postForm<OrganizationProfile>("/organization/logo", formData);
  },

  uploadDeckTemplate: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.postForm<OrganizationProfile>("/organization/deck-template", formData);
  },

  removeDeckTemplate: () =>
    api.delete<OrganizationProfile>("/organization/deck-template"),
};
