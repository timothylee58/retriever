import { bindings, defineConfig, defineContainer, defineWorker, exports } from "@cloudflare/config";

const apiImage = defineContainer({
  name: "retriever",
  image: { dockerfile: "./Dockerfile" },
});

export default defineConfig({
  containers: [apiImage],
  worker: defineWorker({
    name: "retriever",
    entrypoint: "./workers/retriever-api/src/index.ts",
    compatibilityDate: "2026-11-24",
    exports: {
      RetrieverApi: exports.durableObject({
        storage: "sqlite",
        container: apiImage,
      }),
    },
    env: {
      RETRIEVER_API: bindings.durableObject({
        worker: "retriever",
        exportName: "RetrieverApi",
      }),
      DATABASE_URL: bindings.secret(),
      WEB_ORIGIN: bindings.text("*"),
      DRY_RUN: bindings.text("true"),
    },
  }),
});
