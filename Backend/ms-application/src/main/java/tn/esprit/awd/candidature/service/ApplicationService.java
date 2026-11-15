package tn.esprit.awd.candidature.service;

import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import tn.esprit.awd.candidature.client.ApplicationReferences;
import tn.esprit.awd.candidature.dto.ApplicationDto;
import tn.esprit.awd.candidature.entity.Application;
import tn.esprit.awd.candidature.repository.ApplicationRepository;

import java.time.LocalDate;
import java.util.List;

@Service
@Transactional(readOnly = true)
public class ApplicationService {
    private final ApplicationRepository applications;
    private final ApplicationReferences references;
    private final ApplicationEvents events;

    public ApplicationService(ApplicationRepository applications, ApplicationReferences references,
                              ApplicationEvents events) {
        this.applications = applications;
        this.references = references;
        this.events = events;
    }

    public List<ApplicationDto> list(Long candidateId, Long jobId, Pageable pageable) {
        if (candidateId != null) {
            references.candidate(candidateId);
        }
        if (jobId != null) {
            references.job(jobId);
        }
        Page<Application> results;
        if (candidateId != null && jobId != null) {
            results = applications.findByCandidateIdAndJobId(candidateId, jobId, pageable);
        } else if (candidateId != null) {
            results = applications.findByCandidateId(candidateId, pageable);
        } else if (jobId != null) {
            results = applications.findByJobId(jobId, pageable);
        } else {
            results = applications.findAll(pageable);
        }
        return results.map(ApplicationDto::from).getContent();
    }

    public ApplicationDto get(Long id) {
        return ApplicationDto.from(requireApplication(id));
    }

    @Transactional
    public ApplicationDto create(ApplicationDto.Create request) {
        if (applications.existsByCandidateIdAndJobId(request.candidateId(), request.jobId())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Candidate already applied for this job");
        }

        var candidate = references.candidate(request.candidateId());
        var job = references.job(request.jobId());
        if (!job.available()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Job is closed for applications");
        }

        LocalDate date = request.applicationDate() == null ? LocalDate.now() : request.applicationDate();
        var application = applications.save(new Application(request.candidateId(), request.jobId(), date,
                request.motivation()));
        events.created(application, candidate, job);
        return ApplicationDto.from(application);
    }

    @Transactional
    public ApplicationDto update(Long id, ApplicationDto.Update request) {
        var application = requireApplication(id);
        application.update(request.applicationDate(), request.motivation());
        return ApplicationDto.from(application);
    }

    @Transactional
    public ApplicationDto changeStatus(Long id, ApplicationDto.StatusUpdate request) {
        var application = requireApplication(id);
        var previous = application.getStatus();
        if (previous != request.status()) {
            var candidate = references.candidate(application.getCandidateId());
            application.changeStatus(request.status());
            events.statusChanged(application, previous, candidate);
        }
        return ApplicationDto.from(application);
    }

    @Transactional
    public void delete(Long id) {
        applications.delete(requireApplication(id));
    }

    private Application requireApplication(Long id) {
        return applications.findById(id).orElseThrow(() ->
                new ResponseStatusException(HttpStatus.NOT_FOUND, "Application " + id + " was not found"));
    }
}
