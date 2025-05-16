# Deployment Guide for Texas Treasury Query Application

## Pre-deployment Checklist

### Environment Setup
- [ ] Create production `.env` file with all required variables
- [ ] Set up proper API credentials and keys
- [ ] Configure production API URL
- [ ] Enable all security features in production environment

### Security
- [ ] Verify all security headers are properly configured
- [ ] Ensure SSL/TLS is enabled on the web server
- [ ] Configure proper CORS settings for production
- [ ] Set up rate limiting
- [ ] Verify session management and expiry
- [ ] Review and update API authentication

### Application
- [ ] Replace mock data with real API integration
- [ ] Verify all visualizations work with real data
- [ ] Test all filter combinations
- [ ] Verify download functionality
- [ ] Check error handling and logging
- [ ] Test session management

### Infrastructure
- [ ] Set up production Docker container
- [ ] Configure container health checks
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up backup procedures

## Deployment Steps

1. **Environment Preparation**
   ```bash
   # Create production .env file
   cp .env.example .env
   # Edit .env with production values
   ```

2. **Build Docker Image**
   ```bash
   docker build -t texas-treasury-query:latest .
   ```

3. **Run Container**
   ```bash
   docker run -d \
     --name texas-treasury-query \
     -p 8501:8501 \
     --env-file .env \
     --restart unless-stopped \
     texas-treasury-query:latest
   ```

4. **Verify Deployment**
   - Check application logs
   - Verify all endpoints are accessible
   - Test all features with real data
   - Monitor resource usage

## Monitoring and Maintenance

### Health Checks
- Application is accessible at `/health`
- Logs are being written correctly
- API connections are working
- Session management is functioning

### Regular Maintenance
- Monitor log files and rotate as needed
- Check for security updates
- Verify backup procedures
- Review performance metrics

### Troubleshooting
- Check application logs in `streamlit_app/logs/`
- Verify environment variables
- Check API connectivity
- Review security headers

## Rollback Procedure

1. Stop current container:
   ```bash
   docker stop texas-treasury-query
   ```

2. Remove current container:
   ```bash
   docker rm texas-treasury-query
   ```

3. Run previous version:
   ```bash
   docker run -d \
     --name texas-treasury-query \
     -p 8501:8501 \
     --env-file .env \
     --restart unless-stopped \
     texas-treasury-query:previous-version
   ```

## Security Considerations

1. **API Security**
   - Use HTTPS for all API calls
   - Implement proper API key management
   - Set up rate limiting
   - Monitor for suspicious activity

2. **Application Security**
   - Regular security updates
   - Monitor for vulnerabilities
   - Review access logs
   - Implement proper error handling

3. **Data Security**
   - Secure data transmission
   - Proper data sanitization
   - Access control
   - Audit logging

## Support and Contact

For deployment support or issues:
1. Check application logs
2. Review monitoring dashboards
3. Contact system administrator
4. Escalate to development team if needed 