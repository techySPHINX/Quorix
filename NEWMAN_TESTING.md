# Newman API Testing Setup for Evently

This project uses [Newman](https://www.npmjs.com/package/newman) to run automated API tests from the Postman collection for production-grade quality assurance.

## Setup

1. **Install Node.js** (if not already installed):

   - Download from https://nodejs.org/

2. **Install dependencies:**
   ```sh
   npm install
   ```

## Running API Tests

- To run all API tests and generate an HTML report:
  ```sh
  npm run test:api
  ```
- The HTML report will be saved as `newman-report.html` in the project root.

## CI/CD Integration

Add these steps to your CI pipeline:

```sh
npm ci
npm run test:api
```

## Files

- Postman Collection: `docs/postman/evently.postman_collection.json`
- Postman Environment: `docs/postman/evently.postman_environment.json`

## Best Practices

- Keep your Postman collection and environment files up to date with your API changes.
- Review the HTML report after each run for failures and performance insights.
- Integrate this test step into your deployment pipeline for continuous quality.
