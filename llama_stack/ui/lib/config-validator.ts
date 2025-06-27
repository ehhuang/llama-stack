/**
 * Validates environment configuration for the application
 * This is called during server initialization
 */
export function validateServerConfig() {
  if (process.env.NODE_ENV === 'development') {
    console.log('🚀 Starting Llama Stack UI Server...');
    
    // Check for required environment variables
    const requiredEnvVars = {
      GITHUB_CLIENT_ID: process.env.GITHUB_CLIENT_ID,
      GITHUB_CLIENT_SECRET: process.env.GITHUB_CLIENT_SECRET,
      NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
    };

    const missingVars = Object.entries(requiredEnvVars)
      .filter(([_, value]) => !value)
      .map(([key]) => key);

    if (missingVars.length > 0) {
      console.error('❌ Missing required environment variables:');
      missingVars.forEach(varName => {
        console.error(`   - ${varName}`);
      });
      
      if (missingVars.includes('GITHUB_CLIENT_ID') || missingVars.includes('GITHUB_CLIENT_SECRET')) {
        console.error('\n📝 To set up GitHub OAuth:');
        console.error('   1. Go to https://github.com/settings/applications/new');
        console.error('   2. Set Application name: Llama Stack UI (or your preferred name)');
        console.error('   3. Set Homepage URL: http://localhost:8322');
        console.error('   4. Set Authorization callback URL: http://localhost:8322/api/auth/callback/github');
        console.error('   5. Create the app and copy the Client ID and Client Secret');
        console.error('   6. Add them to your .env.local file:');
        console.error('      GITHUB_CLIENT_ID=your_client_id');
        console.error('      GITHUB_CLIENT_SECRET=your_client_secret');
      }

      if (missingVars.includes('NEXTAUTH_SECRET')) {
        console.error('\n🔐 To generate NEXTAUTH_SECRET:');
        console.error('   Run: openssl rand -base64 32');
        console.error('   Add to .env.local: NEXTAUTH_SECRET=your_generated_secret');
      }

      console.error('\n⚠️  The application will run with limited functionality.');
      console.error('   Authentication features will not work properly.\n');
    } else {
      console.log('✅ All required environment variables are configured');
    }

    // Check optional configurations
    const optionalConfigs = {
      NEXTAUTH_URL: process.env.NEXTAUTH_URL || 'http://localhost:8322',
      LLAMA_STACK_BACKEND_URL: process.env.LLAMA_STACK_BACKEND_URL || 'http://localhost:8321',
      LLAMA_STACK_UI_PORT: process.env.LLAMA_STACK_UI_PORT || '8322',
    };

    console.log('\n📋 Configuration:');
    console.log(`   - NextAuth URL: ${optionalConfigs.NEXTAUTH_URL}`);
    console.log(`   - Backend URL: ${optionalConfigs.LLAMA_STACK_BACKEND_URL}`);
    console.log(`   - UI Port: ${optionalConfigs.LLAMA_STACK_UI_PORT}`);
    console.log('');
  }
}

// Call this function when the module is imported
validateServerConfig();